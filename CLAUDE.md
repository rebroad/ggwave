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

# Generate wav/mp4 file for large messages
./examples/ggwave-large-message/ggwave_large_message.py --input input.txt
```

## Python Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv ggwave-venv
source ggwave-venv/bin/activate

# Install ggwave Python module
pip install ggwave numpy
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
  - No longer uses "[PART x/y]" markers (wastes space)
  - Creates WAV files with pauses between chunks (configurable)
  - Generates MP4 videos by default with customizable URL text
  - Uses ultrasound fastest protocol (ID: 5) by default
  - Has dual-mode support (Python library or binary fallback)

## Current Implementation Status
- Core library modifications complete (increased buffer sizes)
- Created working implementation for generating large message audio/video
- Issues identified and resolved:
  1. Removed the "[PART x/y]" markers to maximize data space
  2. Added dual-mode support for both Python module and binary use
  3. Simplified chunking approach for better reliability
  4. Fixed variable name bugs in the script

## Next Steps
1. Set up virtual environment with ggwave module
2. Test improved ggwave_large_message.py with Python module
3. Test with larger chunks (full 600 chars) to verify reception
4. Compare reception quality between different protocols
5. Determine optimal pause duration between chunks
6. Document best practices for large message transmission
7. Final integration into examples directory
