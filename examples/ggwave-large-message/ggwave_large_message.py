#!/usr/bin/env python3

import os
import sys
import argparse
import tempfile
import wave
import time
import subprocess
import numpy as np

# Try to import ggwave, but don't fail if it's not available
USE_GGWAVE_MODULE = False
try:
    import ggwave
    USE_GGWAVE_MODULE = True
    print("Using ggwave Python module")
except ImportError:
    print("ggwave Python module not found, falling back to ggwave-to-file binary")

# Constants
CHUNK_SIZE = 600  # Max characters per chunk (600 as requested)

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

def find_ggwave_binary():
    """Find the ggwave-to-file binary in standard locations."""
    potential_paths = [
        './bin/ggwave-to-file',                          # Current directory
        '../bin/ggwave-to-file',                         # Parent directory
        '../../bin/ggwave-to-file',                      # Grandparent directory
        '../../build/bin/ggwave-to-file',                # Build directory
        '/usr/local/bin/ggwave-to-file',                 # System install
        os.path.expanduser('~/src/ggwave/build/bin/ggwave-to-file')  # Home directory
    ]

    for path in potential_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path

    return None

def generate_wav_for_chunk_with_binary(chunk, output_file, protocol=5, volume=50, sample_rate=48000, quiet=False):
    """Generate a WAV file for a chunk using ggwave-to-file binary."""
    
    if not quiet:
        print(f"  Processing chunk with {len(chunk)} characters using binary")

    try:
        # Find ggwave-to-file binary
        ggwave_bin = find_ggwave_binary()
        
        if not ggwave_bin:
            print("ERROR: Could not find ggwave-to-file binary. Please ensure it's installed and in PATH.")
            return False

        # Create a temporary file for the input
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            tmp.write(chunk)
            tmp_path = tmp.name

        # Run ggwave-to-file with the chunk
        cmd = f"{ggwave_bin} -f{output_file} -p{protocol} -v{volume} -s{sample_rate} < {tmp_path}"

        # Run the command with a timeout
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10
            )
            
            # Clean up temporary input file
            os.unlink(tmp_path)

            # Check if the file was created successfully
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                if not quiet:
                    print(f"  Successfully created WAV file: {output_file}")
                return True
            else:
                print(f"ERROR: Failed to create WAV file: {output_file}")
                if not quiet:
                    print(f"  Command: {cmd}")
                    print(f"  Return code: {result.returncode}")
                    print(f"  STDOUT: {result.stdout.decode('utf-8', errors='replace')}")
                    print(f"  STDERR: {result.stderr.decode('utf-8', errors='replace')}")
                return False

        except Exception as e:
            print(f"ERROR processing chunk: {e}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False

def generate_wav_for_chunk_with_module(chunk, output_file, protocol=5, volume=50, sample_rate=48000, quiet=False, timeout=30):
    """Generate a WAV file for a chunk using ggwave Python module."""
    
    if not quiet:
        print(f"  Processing chunk with {len(chunk)} characters using Python module")
        print(f"  Encoding audio with protocol {protocol}, volume {volume}...")
    
    try:
        import signal
        import threading
        
        # Define a class to handle timeouts
        class TimeoutError(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Audio encoding timed out")
        
        # Set a signal handler for timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        start_time = time.time()
        
        # Generate audio waveform using ggwave
        waveform = ggwave.encode(chunk, protocolId=protocol, volume=volume)
        
        # Reset the alarm
        signal.alarm(0)
        
        encode_time = time.time() - start_time
        if not quiet:
            print(f"  Encoding completed in {encode_time:.2f} seconds")
        
        # Convert byte data into float32
        waveform_float32 = np.frombuffer(waveform, dtype=np.float32)
        
        # Normalize the float32 data to the range of int16
        waveform_int16 = np.int16(waveform_float32 * 32767)
        
        if not quiet:
            print(f"  Writing WAV file...")
        
        # Save the waveform to a .wav file
        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(1)                  # mono audio
            wf.setsampwidth(2)                  # 2 bytes per sample (16-bit PCM)
            wf.setframerate(sample_rate)        # sample rate
            wf.writeframes(waveform_int16.tobytes())  # write the waveform as bytes
            
        # Check if the file was created successfully
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            if not quiet:
                print(f"  Successfully created WAV file: {output_file}")
            return True
        else:
            print(f"ERROR: Failed to create WAV file: {output_file}")
            return False
    
    except TimeoutError:
        print(f"ERROR: Audio encoding timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False
    finally:
        # Make sure to reset the alarm
        signal.alarm(0)

def generate_wav_for_chunk(chunk, output_file, protocol=5, volume=50, sample_rate=48000, quiet=False, timeout=30):
    """Generate a WAV file for a chunk using either the Python module or binary."""
    if USE_GGWAVE_MODULE:
        return generate_wav_for_chunk_with_module(chunk, output_file, protocol, volume, sample_rate, quiet, timeout)
    else:
        return generate_wav_for_chunk_with_binary(chunk, output_file, protocol, volume, sample_rate, quiet)

def create_silence_wav(output_file, duration_seconds, sample_rate=48000):
    """Create a WAV file with silence."""
    n_channels = 1
    sample_width = 2  # 16-bit
    n_frames = int(duration_seconds * sample_rate)

    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setparams((n_channels, sample_width, sample_rate, n_frames, 'NONE', 'not compressed'))
        wav_file.writeframes(bytes(n_frames * sample_width))

def create_video_from_wav(wav_file, video_file, image_path=None, url_text="https://waver.ggerganov.com/"):
    """Create a video file from a WAV file."""
    try:
        # Check if ffmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: ffmpeg is not installed or not in PATH. Cannot create video.")
            return False

        # Create a temporary directory for working files
        temp_dir = tempfile.mkdtemp()

        try:
            # Create a blank image with URL text
            blank_image_path = os.path.join(temp_dir, "blank.png")
            url_text_option = ""
            if url_text:
                # Use a more complex drawtext filter to make the URL more visible
                url_text_option = (
                    f"drawtext=text='{url_text}':fontcolor=white:fontsize=36:box=1:"
                    f"boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=(h-text_h)/2"
                )

            # Create a blank black image with URL
            subprocess.run(
                f"ffmpeg -f lavfi -i color=c=black:s=1280x720:d=1 "
                f"-vf \"{url_text_option}\" -frames:v 1 {blank_image_path}",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            # Get the duration of the WAV file
            with wave.open(wav_file, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / rate

            # Create the video
            subprocess.run(
                f"ffmpeg -loop 1 -i {blank_image_path} -i {wav_file} -c:v libx264 "
                f"-tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest -y {video_file}",
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

def process_large_message(message, output_file, protocol=5, volume=50, sample_rate=48000,
                         add_pauses=True, pause_duration=1.0, quiet=False,
                         create_video=True, image_path=None, url_text="https://waver.ggerganov.com/",
                         timeout=30):
    """Process a large message and create a WAV/video file."""

    # Split the message into chunks
    chunks = split_message(message, CHUNK_SIZE)
    if not quiet:
        print(f"Split message into {len(chunks)} chunks")

    # Determine output files
    base_output = os.path.splitext(output_file)[0]
    wav_output = output_file if not create_video else f"{base_output}_temp.wav"
    video_output = f"{base_output}.mp4" if create_video else None

    # Create temporary directory for chunk WAVs
    temp_dir = tempfile.mkdtemp()
    chunk_files = []

    try:
        # Generate WAV for each chunk
        for i, chunk in enumerate(chunks):
            chunk_file = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk_files.append(chunk_file)

            if not quiet:
                print(f"Processing chunk {i+1}/{len(chunks)}: {len(chunk)} characters")

            success = generate_wav_for_chunk(chunk, chunk_file, protocol, volume, sample_rate, quiet, timeout)

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
            combine_wav_files(interleaved_files, wav_output)
        else:
            # Just combine all chunks without pauses
            combine_wav_files(chunk_files, wav_output)

        if not quiet:
            print(f"Successfully created WAV file: {wav_output}")

        # Create video if requested
        if create_video:
            video_success = create_video_from_wav(wav_output, video_output, image_path, url_text)

            if video_success:
                # Remove the temporary WAV file if video was successfully created
                if os.path.exists(wav_output) and wav_output != output_file:
                    os.unlink(wav_output)
            else:
                print("Warning: Failed to create video, WAV file preserved")

                # If video creation failed but we want video output, rename the WAV to match the requested output
                if wav_output != output_file:
                    os.rename(wav_output, output_file)

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
        default_marker = " (DEFAULT)" if protocol['id'] == 5 else ""
        print(f"{protocol['id']:2d} - {protocol['name']:<15} : {protocol['desc']}{default_marker}")
    print("\nUsage Examples:")
    print("--------------")
    print("  Default (Ultrasound Fastest): ./ggwave_large_message.py -i message.txt")
    print("  Fast audible mode:            ./ggwave_large_message.py -i message.txt -p 1")
    print("  WAV output (no video):        ./ggwave_large_message.py -i message.txt --no-video")
    print("  Custom URL in video:          ./ggwave_large_message.py -i message.txt --url \"https://example.com/\"")
    print("  Custom volume:                ./ggwave_large_message.py -i message.txt -v 75")
    print("  Less verbose output:          ./ggwave_large_message.py -i message.txt --quiet")
    print("  Longer pauses between chunks: ./ggwave_large_message.py -i message.txt -d 2.0")
    print()

def main():
    parser = argparse.ArgumentParser(description="Convert a large message to a WAV or MP4 file using ggwave")
    parser.add_argument("--input", "-i", help="Input text file (if not provided, will read from stdin)")
    parser.add_argument("--output", "-o", default="output.wav", help="Output file base name (default: output.wav)")
    parser.add_argument("--protocol", "-p", type=int, default=5, help="Protocol ID (default: 5, '[U] Fastest' - see --list-protocols)")
    parser.add_argument("--volume", "-v", type=int, default=50, help="Volume (default: 50)")
    parser.add_argument("--sample-rate", "-s", type=int, default=48000, help="Sample rate (default: 48000)")
    parser.add_argument("--no-pauses", action="store_true", help="Don't add pauses between chunks")
    parser.add_argument("--pause-duration", "-d", type=float, default=1.0,
                        help=f"Pause duration in seconds (default: 1.0)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Less verbose output")
    parser.add_argument("--list-protocols", "-l", action="store_true", help="List available protocols and exit")
    parser.add_argument("--no-video", action="store_true", help="Output WAV file instead of MP4 video (video is default)")
    parser.add_argument("--url", help="URL to display in the video (default: https://waver.ggerganov.com/)")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Timeout in seconds for audio encoding (default: 30)")

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
        output_type = "WAV audio" if args.no_video else "MP4 video"
        print(f"Output type: {output_type}")

    # URL to display in the video
    url_text = args.url if args.url else "https://waver.ggerganov.com/"

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
        not args.no_video,  # create_video (default to True)
        None,               # image_path
        url_text,           # URL to display
        args.timeout        # timeout for encoding
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()