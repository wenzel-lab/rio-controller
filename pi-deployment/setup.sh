#!/bin/bash
# Setup script for Raspberry Pi (First time only)
# Run this after copying the deployment package to the Pi
# Installs packages to system Python (no virtual environment)

set -e

echo "Rio Microfluidics Controller - Pi Setup"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Please run this script from the deployment directory."
    exit 1
fi

echo "Step 1: Upgrading pip..."
python3 -m pip install --upgrade pip

echo "Step 2: Installing packages to system Python..."
if [ -f "requirements-webapp-only-32bit.txt" ]; then
    pip install -r requirements-webapp-only-32bit.txt
else
    echo "Warning: requirements file not found, installing manually..."
    pip install "Flask>=2.0.0,<4.0.0"
    pip install "Flask-SocketIO==4.3.2"
    pip install "Werkzeug>=2.0.0,<4.0.0"
    pip install "Jinja2>=3.0.0"
    pip install "MarkupSafe>=2.0.0"
    pip install "itsdangerous>=2.0.0"
    pip install "python-socketio==4.7.1" "python-engineio==3.13.2"
    pip install "eventlet>=0.33.0"
    pip install "opencv-python-headless>=4.5.0,<5.0.0"
    pip install "PyYAML>=6.0"
fi

echo ""
echo "Step 3: Verifying installation..."
pip list | grep -E "Flask|SocketIO|Werkzeug|Jinja2|MarkupSafe|opencv|PyYAML" || echo "Warning: Some packages may not be installed correctly"

echo ""
echo "Setup complete!"
echo ""
echo "To run the application:"
echo "  1. export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric"
echo "  2. export RIO_SIMULATION=false"
echo "  3. export RIO_DROPLET_ANALYSIS_ENABLED=true"
echo "  4. python main.py"
echo ""
echo "Or use the run.sh script after setting environment variables."
echo ""
echo "Note: Packages are installed to system Python. No virtual environment is used."
