# Package Compatibility Guide

## Platform Support

The Rio controller software is designed to work on:
- **Raspberry Pi 32-bit** (Raspberry Pi OS Legacy)
- **Raspberry Pi 64-bit** (Raspberry Pi OS Modern)
- **Mac/PC/Ubuntu** (Simulation mode)

## Requirements Files

### `requirements_32bit.txt` - Raspberry Pi 32-bit
- Uses `picamera==1.13` (legacy library)
- Uses `numpy<2.0.0` (numpy 2.0+ requires 64-bit)
- Compatible with older Raspberry Pi OS

### `requirements_64bit.txt` - Raspberry Pi 64-bit
- Uses `picamera2>=0.3.0` (modern library)
- Uses `numpy>=2.0.0` (latest features)
- Compatible with modern Raspberry Pi OS

### `requirements-simulation.txt` - Mac/PC/Ubuntu
- Excludes Raspberry Pi-specific packages (spidev, RPi.GPIO, picamera)
- Uses opencv-python for simulated camera
- Compatible with all desktop platforms

## Key Package Versions

### Web Framework (All Platforms)
- **Flask**: 2.0.0 - 3.x (compatible across platforms)
- **Flask-SocketIO**: 5.0.0+ (compatible across platforms)
- **Werkzeug**: 2.0.0 - 3.x (compatible across platforms)

### Image Processing
- **Pillow**: 9.0.0+ (all platforms)
- **opencv-python**: 4.5.0+ (simulation and 64-bit), 4.5.0-4.11.0 (32-bit)
- **numpy**: 
  - 1.19.0 - 1.x (32-bit)
  - 2.0.0+ (64-bit)
  - 1.19.0+ (simulation)

### Raspberry Pi Hardware
- **spidev**: 3.6 (all Pi versions)
- **RPi.GPIO**: 0.7.1 (all Pi versions)
- **picamera**: 1.13 (32-bit only)
- **picamera2**: 0.3.0+ (64-bit only)

## Compatibility Matrix

| Package | 32-bit Pi | 64-bit Pi | Mac/PC/Ubuntu |
|---------|-----------|-----------|---------------|
| Flask | ✅ 2.0-3.x | ✅ 3.0-3.x | ✅ 2.0-3.x |
| Flask-SocketIO | ✅ 5.0+ | ✅ 5.4+ | ✅ 5.0+ |
| numpy | ✅ 1.19-1.x | ✅ 2.0+ | ✅ 1.19+ |
| opencv-python | ✅ 4.5-4.11 | ✅ 4.10+ | ✅ 4.5+ |
| picamera | ✅ 1.13 | ❌ | ❌ |
| picamera2 | ❌ | ✅ 0.3+ | ❌ |
| spidev | ✅ 3.6 | ✅ 3.6 | ❌ (simulated) |
| RPi.GPIO | ✅ 0.7.1 | ✅ 0.7.1 | ❌ (simulated) |

## Installation Instructions

### Raspberry Pi 32-bit
```bash
mamba create -n rio-controller python=3.10 -y
mamba activate rio-controller
pip install -r requirements_32bit.txt
```

### Raspberry Pi 64-bit
```bash
mamba create -n rio-controller python=3.10 -y
mamba activate rio-controller
pip install -r requirements_64bit.txt
```

### Mac/PC/Ubuntu (Simulation)
```bash
mamba create -n rio-controller python=3.10 -y
mamba activate rio-controller
pip install -r requirements-simulation.txt
```

## Version Conflicts

If you encounter version conflicts:

1. **numpy 2.0 on 32-bit**: Use `requirements_32bit.txt` which pins numpy<2.0
2. **picamera vs picamera2**: Only install the one for your system
3. **Flask version**: All versions 2.0+ are compatible, but 3.x has better features

## Testing Compatibility

After installation, verify:
```bash
python -c "import flask; import flask_socketio; print('Web framework OK')"
python -c "import numpy; print(f'numpy {numpy.__version__} OK')"
python -c "import cv2; print('opencv OK')"  # Simulation only
python -c "import picamera; print('picamera OK')"  # 32-bit only
python -c "import picamera2; print('picamera2 OK')"  # 64-bit only
```

