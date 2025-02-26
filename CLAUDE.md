# ggwave Project Commands

## Build Commands
```bash
# Basic build
mkdir -p build && cd build
cmake ..
make

# Build with Emscripten
mkdir -p build && cd build
emcmake cmake ..
make
```

## Run Commands
```bash
# Run CLI tool
./bin/ggwave-cli

# Run Waver app (if installed)
waver

# Generate wav file for large message
./examples/ggwave-large-message/ggwave_large_message.py --input input.txt --output output.wav
```

## Code Style Preferences
- Follow existing code style in the project
- Maintain consistent indentation
- Keep line lengths reasonable

## Project Structure Notes
- Core library in src/
- Examples in examples/
- Bindings for Python, JavaScript, and iOS in bindings/
- Tests in tests/

## Project Modifications
- Increased message size limits:
  - kMaxLengthVariable: 140 → 600 characters
  - kMaxDataSize: 256 → 1024 bytes
- Added ggwave_large_message.py tool for handling large messages:
  - Splits messages into chunks of up to 600 characters
  - Creates WAV files with optional pauses between chunks
  - Can generate video files with ffmpeg (MP4)
  - Supports all protocol types (0-11)