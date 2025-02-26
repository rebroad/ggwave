#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import tempfile
import wave
import time
import json
import re

# Constants
CHUNK_SIZE = 600  # Max characters per chunk (must match GGWave::kMaxLengthVariable in ggwave.h)
PAUSE_SECONDS = 1.0  # Pause duration between chunks in seconds

# Protocol descriptions
PROTOCOLS = [
    {"id": 0, "name": "Normal", "desc": "Standard audible mode with good reliability"},
    {"id": 1, "name": "Fast", "desc": "Faster audible mode with good reliability"},
    {"id": 2, "name": "Fastest", "desc": "Fastest audible mode with reduced reliability"},
    {"id": 3, "name": "[U] Normal", "desc": "Standard ultrasound mode with good reliability"},
    {"id": 4, "name": "[U] Fast", "desc": "Faster ultrasound mode with good reliability"},
    {"id": 5, "name": "[U] Fastest", "desc": "Fastest ultrasound mode with reduced reliability"},
    {"id": 6, "name": "[DT] Normal", "desc": "Standard dual-tone mode with good reliability"},
    {"id": 7, "name": "[DT] Fast", "desc": "Faster dual-tone mode with good reliability"},
    {"id": 8, "name": "[DT] Fastest", "desc": "Fastest dual-tone mode with reduced reliability"},
    {"id": 9, "name": "[MT] Normal", "desc": "Standard mono-tone mode with good reliability"},
    {"id": 10, "name": "[MT] Fast", "desc": "Faster mono-tone mode with good reliability"},
    {"id": 11, "name": "[MT] Fastest", "desc": "Fastest mono-tone mode with reduced reliability"}
]

def split_message(message, chunk_size=CHUNK_SIZE):
    """Split a message into chunks of a specified size."""
    # Replace any newlines with spaces to treat the message as a continuous text
    message = message.replace('\n', ' ')
    
    chunks = []
    current_pos = 0
    
    while current_pos < len(message):
        # Get a potential chunk
        potential_chunk = message[current_pos:current_pos + chunk_size]
        
        # Keep reducing the chunk size until it fits within the UTF-8 byte limit
        while len(potential_chunk.encode('utf-8')) > chunk_size:
            potential_chunk = potential_chunk[:-1]  # Remove the last character
        
        if potential_chunk:  # Only add non-empty chunks
            chunks.append(potential_chunk)
            current_pos += len(potential_chunk)
        else:
            # If we couldn't make a chunk (e.g., a single emoji took too many bytes)
            # Skip this character and continue
            current_pos += 1
    
    return chunks

def generate_wav_for_chunk(chunk, output_file, protocol=1, volume=50, sample_rate=48000, quiet=False):
    """Generate a WAV file for a single chunk using ggwave-to-file."""
    
    try:
        # Always print diagnostic info for debugging
        print(f"DEBUG: Chunk length: {len(chunk)} characters, {len(chunk.encode('utf-8'))} bytes")
        
        # Create a temporary file for the chunk data
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as tmp:
            tmp.write(chunk)
            tmp_name = tmp.name
        
        print(f"DEBUG: Wrote chunk to temporary file: {tmp_name}")
        
        # Find ggwave-to-file binary
        # Look in multiple potential locations
        potential_paths = [
            './bin/ggwave-to-file',                          # Current directory
            '../bin/ggwave-to-file',                         # Parent directory
            '../../bin/ggwave-to-file',                      # Grandparent directory
            '../../build/bin/ggwave-to-file',                # Build directory
            '/usr/local/bin/ggwave-to-file',                 # System install
            os.path.expanduser('~/src/ggwave/build/bin/ggwave-to-file')  # Home directory
        ]
        
        ggwave_bin = None
        for path in potential_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                ggwave_bin = path
                break
        
        if not ggwave_bin:
            print("ERROR: Could not find ggwave-to-file binary. Please ensure it's installed and in PATH.")
            return False
            
        # Run ggwave-to-file with a simple, direct approach
        cmd = [
            ggwave_bin,
            f'-f{output_file}',
            f'-p{protocol}',
            f'-v{volume}',
            f'-s{sample_rate}'
        ]
        
        print(f"DEBUG: Running command: {' '.join(cmd)}")
        
        # First, let's run it and examine ALL output for debugging
        full_cmd = f"{' '.join(cmd)} < {tmp_name}"
        print(f"DEBUG: Full command: {full_cmd}")
        
        result = subprocess.run(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print ALL output for debugging
        print(f"DEBUG: Return code: {result.returncode}")
        print(f"DEBUG: STDOUT: {result.stdout}")
        print(f"DEBUG: STDERR: {result.stderr}")
        
        # Check if the file was created successfully
        if os.path.exists(output_file):
            print(f"DEBUG: Successfully created output file: {output_file}")
            os.unlink(tmp_name)  # Clean up temporary file
            return True
        else:
            print(f"ERROR: Failed to create WAV file: {output_file}")
            os.unlink(tmp_name)  # Clean up temporary file
            return False
    
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

def create_silence_wav(output_file, duration_seconds, sample_rate=48000):
    """Create a WAV file with silence."""
    # Create a WAV file with silence (all zeros)
    n_channels = 1
    sample_width = 2  # 16-bit
    n_frames = int(duration_seconds * sample_rate)
    
    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setparams((n_channels, sample_width, sample_rate, n_frames, 'NONE', 'not compressed'))
        wav_file.writeframes(bytes(n_frames * sample_width))

def combine_wav_files(wav_files, output_file):
    """Combine multiple WAV files into one."""
    data = []
    params = None
    
    # Read all WAV files
    for wav_file in wav_files:
        with wave.open(wav_file, 'rb') as wf:
            if params is None:
                params = wf.getparams()
            data.append(wf.readframes(wf.getnframes()))
    
    # Write combined WAV file
    with wave.open(output_file, 'wb') as wf:
        wf.setparams(params)
        for frame_data in data:
            wf.writeframes(frame_data)

def create_video_from_wav(wav_file, video_file, image_path=None, url_text=None):
    """Create a video file from a WAV file."""
    try:
        # Check if ffmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Error: ffmpeg is not installed or not in PATH. Cannot create video.")
            return False
        
        # Create a temporary directory for working files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # If an image is provided, use it; otherwise, create a blank image with optional URL text
            input_image = None
            if image_path and os.path.exists(image_path):
                input_image = image_path
            else:
                # Create a blank image with URL text if provided
                blank_image_path = os.path.join(temp_dir, "blank.png")
                url_text_option = ""
                if url_text:
                    url_text_option = f"-vf \"drawtext=text='{url_text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2\""
                
                # Create a blank black image
                subprocess.run(
                    f"ffmpeg -f lavfi -i color=c=black:s=640x360:d=1 {url_text_option} -frames:v 1 {blank_image_path}",
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
                )
                input_image = blank_image_path
            
            # Now create the video from the WAV file and the image
            # Get the duration of the WAV file
            with wave.open(wav_file, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / rate
            
            # Create the video
            subprocess.run(
                f"ffmpeg -loop 1 -i {input_image} -i {wav_file} -c:v libx264 -tune stillimage "
                f"-c:a aac -b:a 192k -pix_fmt yuv420p -shortest -y {video_file}",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            
            print(f"Successfully created video file: {video_file}")
            return True
            
        finally:
            # Clean up temporary directory
            try:
                for f in os.listdir(temp_dir):
                    os.unlink(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
            except OSError as e:
                print(f"Warning: Could not clean up temporary files: {e}")
    
    except Exception as e:
        print(f"Error creating video: {e}")
        return False

def process_large_message(message, output_file, protocol=1, volume=50, sample_rate=48000, 
                         add_pauses=True, pause_duration=PAUSE_SECONDS, quiet=False, 
                         create_video=False, image_path=None, url_text=None):
    """Process a large message and create a WAV file and optionally a video file."""
    
    # Split the message into chunks
    chunks = split_message(message, CHUNK_SIZE)
    if not quiet:
        print(f"Split message into {len(chunks)} chunks")
    
    # Create temporary directory for chunk WAVs
    temp_dir = tempfile.mkdtemp()
    chunk_files = []
    
    try:
        # Generate WAV for each chunk
        for i, chunk in enumerate(chunks):
            chunk_file = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk_files.append(chunk_file)
            
            if not quiet:
                print(f"Processing chunk {i+1}/{len(chunks)}: {chunk}")
            success = generate_wav_for_chunk(chunk, chunk_file, protocol, volume, sample_rate, quiet)
            
            if not success:
                print(f"Failed to process chunk {i+1}")
                return False
        
        # If pauses are requested, create silence WAVs and interleave them
        if add_pauses and len(chunks) > 1:
            silence_file = os.path.join(temp_dir, "silence.wav")
            create_silence_wav(silence_file, pause_duration, sample_rate)
            
            # Create the interleaved list of files (chunk1, silence, chunk2, silence, ...)
            interleaved_files = []
            for i in range(len(chunk_files)):
                interleaved_files.append(chunk_files[i])
                if i < len(chunk_files) - 1:  # Don't add silence after the last chunk
                    interleaved_files.append(silence_file)
            
            # Combine all files
            combine_wav_files(interleaved_files, output_file)
        else:
            # Just combine all chunks without pauses
            combine_wav_files(chunk_files, output_file)
        
        if not quiet:
            print(f"Successfully created WAV file: {output_file}")
        
        # Create video if requested
        if create_video:
            # Get the base output name without extension
            base_output = os.path.splitext(output_file)[0]
            video_file = f"{base_output}.mp4"
            create_video_from_wav(output_file, video_file, image_path, url_text)
            
        return True
    
    finally:
        # Clean up temporary files
        for file in chunk_files:
            if os.path.exists(file):
                os.unlink(file)
        
        # Also remove silence file if it exists
        silence_file = os.path.join(temp_dir, "silence.wav")
        if os.path.exists(silence_file):
            os.unlink(silence_file)
        
        try:
            os.rmdir(temp_dir)
        except OSError as e:
            if not quiet:
                print(f"Warning: Could not remove temporary directory: {e}")

def list_protocols():
    """Display information about available protocols."""
    print("\nAvailable Protocols:")
    print("-------------------")
    for protocol in PROTOCOLS:
        print(f"{protocol['id']:2d} - {protocol['name']:<15} : {protocol['desc']}")
    print("\nUsage Examples:")
    print("--------------")
    print("  Default (Ultrasound Fastest): ./ggwave_large_message.py -i message.txt")
    print("  Fast audible mode:            ./ggwave_large_message.py -i message.txt -p 1")
    print("  Audio only (no video):        ./ggwave_large_message.py -i message.txt --no-video")
    print("  Custom URL in video:          ./ggwave_large_message.py -i message.txt --url \"https://example.com/\"")
    print("  Less verbose output:          ./ggwave_large_message.py -i message.txt --quiet")
    print("  Longer pauses between chunks: ./ggwave_large_message.py -i message.txt -d 2.0")
    print()

def main():
    parser = argparse.ArgumentParser(description="Convert a large message to a WAV/video file using ggwave")
    parser.add_argument("--input", "-i", help="Input text file (if not provided, will read from stdin)")
    parser.add_argument("--output", "-o", default="output.wav", help="Output WAV file (default: output.wav)")
    parser.add_argument("--protocol", "-p", type=int, default=5, help="Protocol ID (default: 5, '[U] Fastest' - see --list-protocols)")
    parser.add_argument("--volume", "-v", type=int, default=50, help="Volume (default: 50)")
    parser.add_argument("--sample-rate", "-s", type=int, default=48000, help="Sample rate (default: 48000)")
    parser.add_argument("--no-pauses", action="store_true", help="Don't add pauses between chunks")
    parser.add_argument("--pause-duration", "-d", type=float, default=PAUSE_SECONDS, 
                        help=f"Pause duration in seconds (default: {PAUSE_SECONDS})")
    parser.add_argument("--quiet", "-q", action="store_true", help="Less verbose output")
    parser.add_argument("--list-protocols", "-l", action="store_true", help="List available protocols and exit")
    parser.add_argument("--no-video", action="store_true", help="Do not create a video file (video is generated by default)")
    parser.add_argument("--image", help="Image file to use for video (if not provided, a blank image will be used)")
    parser.add_argument("--url", default="https://waver.ggerganov.com/", 
                       help="URL to display in the video (default: https://waver.ggerganov.com/)")

    args = parser.parse_args()
    
    # If the list-protocols flag is set, just display protocol info and exit
    if args.list_protocols:
        list_protocols()
        sys.exit(0)
    
    # Validate the protocol ID
    if args.protocol < 0 or args.protocol >= len(PROTOCOLS):
        print(f"Error: Invalid protocol ID {args.protocol}. Use --list-protocols to see available options.")
        sys.exit(1)
    
    # Protocol name for informational purposes
    protocol_name = PROTOCOLS[args.protocol]['name']
    
    # Read message from file or stdin
    if args.input:
        with open(args.input, 'r') as f:
            message = f.read()
    else:
        if not args.quiet:
            print("Enter your message (press Ctrl+D when finished):")
        message = sys.stdin.read()
    
    if not args.quiet:
        print(f"Using protocol: {args.protocol} ({protocol_name})")
    
    # Process the message
    success = process_large_message(
        message, 
        args.output, 
        args.protocol, 
        args.volume, 
        args.sample_rate, 
        not args.no_pauses, 
        args.pause_duration,
        args.quiet,
        not args.no_video,  # Default to generating video unless --no-video is specified
        args.image,
        args.url if not args.no_video else None
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
