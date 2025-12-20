# Installed Packages and Versions

**Documentation Date:** December 20, 2025  
**System:** Raspberry Pi (aarch64, Linux)  
**Python Version:** 3.9.2  
**Virtual Environment:** `venv-rio` (located at `/home/pi/rio-controller/venv-rio`)

## Installation Context

This document reflects the **actual installed packages** after troubleshooting installation issues. The initial requirements file (`requirements-webapp-only-32bit.txt`) specified version ranges, but due to compatibility issues encountered during setup, some packages were installed with specific versions that differ from the original requirements.

## Current Package Versions

### Web Framework
```
Flask==3.1.2
Flask-SocketIO==5.5.1
Werkzeug==3.1.4
Jinja2==3.1.6
MarkupSafe==3.0.3
itsdangerous==2.2.0
click==8.1.8
```

### WebSocket Support
```
python-socketio==5.15.0
python-engineio==4.12.3
eventlet==0.40.4
greenlet==3.2.4
simple-websocket==1.1.0
wsproto==1.2.0
```

### Image Processing
```
opencv-python-headless==4.12.0.88
Pillow==9.5.0
numpy==1.19.5
```

### Configuration & Utilities
```
PyYAML==6.0.3
blinker==1.9.0
dnspython==2.7.0
h11==0.16.0
importlib_metadata==8.7.0
zipp==3.23.0
bidict==0.23.1
```

### Raspberry Pi Hardware Interface
```
RPi.GPIO==0.7.1
spidev==3.8
picamera==1.13
```

### Python Package Management
```
pip==25.3
setuptools==44.1.1
pkg_resources==0.0.0
```

## Notes on Package Versions

### Key Observations

1. **numpy==1.19.5**: Pinned to version 1.19.5 (compatible with Python 3.9 and picamera). Version 2.x is not compatible with picamera library.

2. **opencv-python-headless==4.12.0.88**: Using headless version (no GUI dependencies) suitable for server environments. Version 4.12.x was installed successfully.

3. **eventlet==0.40.4**: Upgraded from initial version (0.33.x mentioned in requirements). Required for Flask-SocketIO async support.

4. **picamera==1.13**: System-wide installation, but accessible in virtual environment. Required for Raspberry Pi Camera interface (legacy API, 32-bit compatible).

5. **Flask-SocketIO==5.5.1**: Compatible with eventlet 0.40.4 and Python 3.9.

6. **Pillow==9.5.0**: Stable version compatible with numpy 1.19.5 and opencv-python-headless.

### Installation Method

Packages were installed in a virtual environment to avoid root installations and potential system conflicts:

```bash
python3 -m venv venv-rio
source venv-rio/bin/activate
pip install -r requirements-webapp-only-32bit.txt
```

Note: Some packages (picamera, RPi.GPIO, spidev) may need to be installed system-wide first, then accessed through the virtual environment.

## Troubleshooting Notes

During initial installation, the following issues were encountered and resolved:

1. **numpy compatibility**: Had to ensure numpy < 2.0.0 for picamera compatibility
2. **opencv-python vs opencv-python-headless**: Used headless version to avoid X11 dependencies
3. **eventlet version**: Required upgrade for compatibility with newer Flask-SocketIO
4. **Virtual environment isolation**: Ensured packages installed in venv, not system-wide

## Package Dependency Graph (Simplified)

```
Flask (3.1.2)
├── Werkzeug (3.1.4)
├── Jinja2 (3.1.6)
├── click (8.1.8)
├── itsdangerous (2.2.0)
└── MarkupSafe (3.0.3)

Flask-SocketIO (5.5.1)
├── Flask (3.1.2)
├── python-socketio (5.15.0)
│   ├── python-engineio (4.12.3)
│   ├── bidict (0.23.1)
│   └── simple-websocket (1.1.0)
└── eventlet (0.40.4)
    └── greenlet (3.2.4)

Image Processing Stack
├── opencv-python-headless (4.12.0.88)
│   └── numpy (1.19.5)
├── Pillow (9.5.0)
└── numpy (1.19.5) [also used by picamera]

Hardware Interface
├── picamera (1.13) [system-wide, legacy API]
├── RPi.GPIO (0.7.1)
└── spidev (3.8)
```

## Regenerating This List

To regenerate the current package list:

```bash
cd /home/pi/rio-controller
source venv-rio/bin/activate
pip list --format=freeze | sort > current_packages.txt
```

## Replication Instructions

To replicate this environment on another Raspberry Pi:

1. Create virtual environment:
   ```bash
   python3 -m venv venv-rio
   source venv-rio/bin/activate
   ```

2. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

3. Install packages (using requirements file with version ranges):
   ```bash
   pip install -r requirements-webapp-only-32bit.txt
   ```

4. If compatibility issues occur, install specific versions:
   ```bash
   pip install numpy==1.19.5  # If needed for picamera compatibility
   pip install opencv-python-headless==4.12.0.88  # If needed
   ```

5. Verify installation:
   ```bash
   pip list
   ```

