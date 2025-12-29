#!/bin/bash
# Simple script for Socket.IO upgrade test on Raspberry Pi
# Run this from the rio-controller directory

set -e

echo "=========================================="
echo "Socket.IO Upgrade Test - Raspberry Pi"
echo "=========================================="
echo ""

# Check if we're in the right directory
# The file should be in the current directory (after rsync, this is ~/rio-controller)
if [ -f "requirements-webapp-only-32bit-upgraded.txt" ]; then
    REQ_FILE="requirements-webapp-only-32bit-upgraded.txt"
else
    echo "ERROR: requirements file not found!"
    echo "Current directory: $(pwd)"
    echo ""
    echo "Please run this script from the rio-controller directory on the Pi:"
    echo "  cd ~/rio-controller"
    echo "  ./SOCKETIO_UPGRADE_PI.sh"
    echo ""
    echo "The requirements file should be in the same directory after rsync."
    exit 1
fi

echo "✓ Found requirements file: $REQ_FILE"
echo ""

# Create virtual environment with system site packages
# This allows access to system-wide hardware packages (spidev, RPi.GPIO, picamera)
# while still isolating the Socket.IO packages for testing
if [ ! -d "venv-socketio-test" ]; then
    echo "Creating virtual environment with system site packages..."
    echo "(This allows access to hardware libraries like spidev, RPi.GPIO, picamera)"
    python3 -m venv --system-site-packages venv-socketio-test
    echo "✓ Virtual environment created"
else
    echo "Virtual environment already exists"
    echo "Note: If you have issues, delete it and recreate: rm -rf venv-socketio-test"
fi

# Activate and install
echo ""
echo "Activating virtual environment..."
source venv-socketio-test/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing upgraded Socket.IO packages..."
echo "(This may take a few minutes...)"
pip install -r "$REQ_FILE"

# Force install eventlet in venv to override system version
# This is needed because --system-site-packages sees system eventlet first
# Install dependencies first, then force reinstall eventlet
echo ""
echo "Ensuring eventlet is installed in venv (overrides system version)..."
pip install "dnspython>=1.15.0" "greenlet>=0.3" "six>=1.10.0"
pip install --force-reinstall --no-deps "eventlet>=0.33.0,<1.0.0"

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Installed versions:"
python3 -c "
try:
    import flask_socketio
    import socketio
    import engineio
    # Flask-SocketIO 5.x uses __version__ but may need to check package metadata
    try:
        fs_version = flask_socketio.__version__
    except AttributeError:
        import pkg_resources
        fs_version = pkg_resources.get_distribution('Flask-SocketIO').version
    print(f'  Flask-SocketIO: {fs_version}')
    print(f'  python-socketio: {socketio.__version__}')
    print(f'  python-engineio: {engineio.__version__}')
except Exception as e:
    print(f'  Error checking versions: {e}')
    print('  (But packages may still be installed correctly)')
"

echo ""
echo "Next steps:"
echo "1. Test the application:"
echo "   source venv-socketio-test/bin/activate"
echo "   export RIO_STROBE_CONTROL_MODE=strobe-centric"
echo "   export RIO_SIMULATION=false"
echo "   export RIO_DROPLET_ANALYSIS_ENABLED=true"
echo "   python main.py"
echo ""
echo "2. Open browser and test all Socket.IO features"
echo ""
echo "3. To rollback:"
echo "   deactivate"
echo "   # Use your original environment (system Python or venv-rio)"
echo ""

