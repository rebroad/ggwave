# ggwave-large-message

A utility for transmitting large messages via sound using the ggwave library. This tool splits large messages into chunks and encodes them as audio, with optional pauses between segments.

## Features

- Handles messages of any size by automatically splitting into chunks
- Respects UTF-8 encoding when splitting messages
- Adds configurable pauses between chunks for reliable transmission
- Supports all ggwave transmission protocols
- Can generate WAV audio files or MP4 video files (requires ffmpeg)
- Customizable volume and sample rate settings

## Requirements

- Python 3.6+
- ggwave library with `ggwave-to-file` binary
- ffmpeg (optional, for video output)

## Usage

```bash
# Basic usage (outputs WAV file)
./ggwave_large_message.py --input message.txt --output message.wav

# Create video with custom URL
./ggwave_large_message.py --input message.txt --output message.wav --url "https://example.com/"

# Use a specific protocol (see --list-protocols for all options)
./ggwave_large_message.py --input message.txt --protocol 1

# List all available protocols
./ggwave_large_message.py --list-protocols

# Skip video creation
./ggwave_large_message.py --input message.txt --no-video
```

## Notes

- Default protocol is 5 ([U] Fastest) which uses ultrasound frequencies
- Default pause between chunks is 1 second
- Message chunks are limited to 600 characters each (matching ggwave library limits)