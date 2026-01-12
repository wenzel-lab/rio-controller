#!/bin/bash
# Create a minimal deployment package for Raspberry Pi
# Excludes tests, simulation, documentation, and development files

set -e

# Get script directory and repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to repo root for all operations
cd "$REPO_ROOT"

DEPLOY_DIR="pi-deployment"
SOURCE_DIR="software"

echo "Creating Raspberry Pi deployment package..."
echo "Repository root: $REPO_ROOT"

# Remove old deployment if it exists
if [ -d "$DEPLOY_DIR" ]; then
    echo "Removing old deployment directory..."
    rm -rf "$DEPLOY_DIR"
fi

# Create deployment directory structure
mkdir -p "$DEPLOY_DIR"

# Copy essential Python files
echo "Copying essential files..."

# Main entry point
cp "$SOURCE_DIR/main.py" "$DEPLOY_DIR/"

# Path bootstrapper (needed for imports)
cp "$SOURCE_DIR/path_bootstrap.py" "$DEPLOY_DIR/"

# Configuration
cp "$SOURCE_DIR/config.py" "$DEPLOY_DIR/"

# Controllers (all Python files, exclude __pycache__)
cp -r "$SOURCE_DIR/controllers" "$DEPLOY_DIR/"
find "$DEPLOY_DIR/controllers" -name "*.pyc" -delete
find "$DEPLOY_DIR/controllers" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Drivers (all Python files)
cp -r "$SOURCE_DIR/drivers" "$DEPLOY_DIR/"
find "$DEPLOY_DIR/drivers" -name "*.pyc" -delete
find "$DEPLOY_DIR/drivers" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
# Remove test files from drivers/camera
find "$DEPLOY_DIR/drivers/camera" -name "test_*.py" -delete 2>/dev/null || true

# Droplet detection (all Python files, exclude tests)
cp -r "$SOURCE_DIR/droplet-detection" "$DEPLOY_DIR/"
find "$DEPLOY_DIR/droplet-detection" -name "*.pyc" -delete
find "$DEPLOY_DIR/droplet-detection" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
# Remove test and benchmark files
find "$DEPLOY_DIR/droplet-detection" -name "test_*.py" -delete 2>/dev/null || true
find "$DEPLOY_DIR/droplet-detection" -name "benchmark.py" -delete 2>/dev/null || true
find "$DEPLOY_DIR/droplet-detection" -name "optimize.py" -delete 2>/dev/null || true
find "$DEPLOY_DIR/droplet-detection" -name "run_tests.sh" -delete 2>/dev/null || true

# Web app (all files)
cp -r "$SOURCE_DIR/rio-webapp" "$DEPLOY_DIR/"
find "$DEPLOY_DIR/rio-webapp" -name "*.pyc" -delete
find "$DEPLOY_DIR/rio-webapp" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# API (if present)
if [ -d "$SOURCE_DIR/api" ]; then
    cp -r "$SOURCE_DIR/api" "$DEPLOY_DIR/"
    find "$DEPLOY_DIR/api" -name "*.pyc" -delete
    find "$DEPLOY_DIR/api" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
fi

# Configurations
cp -r "$SOURCE_DIR/configurations" "$DEPLOY_DIR/"

# Requirements file
# Copy requirements file (works for both 32-bit and 64-bit Pi)
cp "$SOURCE_DIR/requirements-pi.txt" "$DEPLOY_DIR/" 2>/dev/null || true
# API requirements (optional API server on Pi)
cp "$SOURCE_DIR/requirements-api.txt" "$DEPLOY_DIR/" 2>/dev/null || true

# Copy desktop entry if it exists (moved to rio-webapp/)
if [ -f "$SOURCE_DIR/rio-webapp/omw.desktop" ]; then
    cp "$SOURCE_DIR/rio-webapp/omw.desktop" "$DEPLOY_DIR/"
fi

# Create setup script for Pi (using the existing content from the original script)
cat > "$DEPLOY_DIR/setup.sh" << 'EOF'
#!/bin/bash
# Setup script for Raspberry Pi (First time only)
# Run this after copying the deployment package to the Pi
# Installs packages to system Python (no virtual environment)

# Don't exit on errors - we want to continue even if some checks fail
set +e

echo "Rio Microfluidics Controller - Pi Setup"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Please run this script from the deployment directory."
    exit 1
fi

echo "Step 1: Checking and installing system packages (apt)..."
echo "This requires sudo privileges."
echo ""

# Check system clock (common issue on fresh Pi - causes SSL failures)
if [ "$(date +%s)" -lt "$(date -d '2020-01-01' +%s 2>/dev/null || echo 0)" ]; then
    echo "⚠ Warning: System clock appears to be incorrect. This will cause SSL/certificate errors."
    echo "           Fix with: sudo date -s '$(date -R)' (requires network)"
    echo "           Or set manually: sudo date -s 'YYYY-MM-DD HH:MM:SS'"
    echo ""
fi

# Check if Raspberry Pi repository is configured (for libatlas-base-dev)
if ! grep -q "raspberrypi.org" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null; then
    echo "Warning: Raspberry Pi Foundation repository may not be configured."
    echo "         Some packages (libatlas-base-dev) may not be available."
    echo "         If installation fails, add: deb http://archive.raspberrypi.org/debian/ bullseye main"
    echo ""
fi

# Update package lists (continue even if network fails - use cached packages)
sudo apt-get update || {
    echo "Warning: apt-get update failed (network issue?). Continuing with cached package lists..."
}

# Install system packages needed for hardware and droplet detection
echo "Installing hardware packages..."
sudo apt-get install -y python3-spidev python3-rpi.gpio python3-picamera python3-numpy || {
    echo "Warning: Some hardware packages failed to install. Continuing..."
}

# Install OpenCV from apt (fast, pre-built) - critical for droplet detection
echo "Installing OpenCV from apt (fast, pre-built)..."
sudo apt-get install -y python3-opencv || {
    echo "⚠ Warning: python3-opencv installation failed (possibly network issue)."
    echo "           Try: sudo apt-get install -y python3-opencv --fix-missing"
    echo "           Or: sudo apt-get update && sudo apt-get install -y python3-opencv"
}

# Verify OpenCV from apt (fast, pre-built)
if python3 -c "import cv2; print('OpenCV version:', cv2.__version__)" 2>/dev/null; then
    echo "✓ OpenCV installed from apt (fast, pre-built)"
else
    echo "⚠ ERROR: python3-opencv installation failed. Droplet detection will not work."
    echo "         Install manually: sudo apt-get install -y python3-opencv"
    echo "         Then verify: python3 -c 'import cv2; print(cv2.__version__)'"
fi

echo "Installing BLAS/LAPACK for droplet detection..."
sudo apt-get install -y libatlas-base-dev libatlas3-base libblas3 liblapack3 || {
    echo "Warning: BLAS/LAPACK packages failed to install. Droplet detection may not work."
    echo "         Try: sudo apt-get install -y libatlas-base-dev libatlas3-base"
}

# Verify libcblas.so.3 is available
if ! ldconfig -p | grep -q libcblas.so.3; then
    echo "Warning: libcblas.so.3 not found. Droplet detection will fail."
    echo "         Run: sudo ldconfig"
else
    echo "✓ libcblas.so.3 found"
fi

echo ""
echo "Step 2: Checking legacy camera configuration..."
if [ -f /boot/config.txt ]; then
    if grep -q "^start_x=1" /boot/config.txt; then
        echo "✓ Legacy camera appears to be enabled in /boot/config.txt"
    else
        echo "⚠ Warning: Legacy camera may not be enabled."
        echo "           Run: sudo raspi-config → Interface Options → Legacy Camera → Enable"
        echo "           Then reboot before running the application."
    fi
else
    echo "⚠ Warning: Cannot check /boot/config.txt. Ensure legacy camera is enabled."
fi

echo ""
echo "Step 3: Cleaning GPIO state..."
python3 - <<'PYEOF' || echo "Note: GPIO cleanup completed (warnings are normal if no GPIO was in use)"
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
try:
    GPIO.cleanup()
except:
    pass
try:
    GPIO.setmode(GPIO.BOARD)
except:
    pass
PYEOF

echo ""
echo "Step 4: Upgrading pip..."
# Upgrade pip with trusted hosts to avoid SSL issues (common on fresh Pi with wrong system clock)
python3 -m pip install --user --upgrade --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host www.piwheels.org pip wheel || {
    echo "Warning: pip upgrade failed (possibly network/SSL issue). Trying without SSL verification..."
    python3 -m pip install --user --upgrade --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host www.piwheels.org --trusted-host pypi.python.org pip wheel || {
        echo "Error: pip upgrade failed. Check network connectivity and system clock."
        echo "       If system clock is wrong, run: sudo date -s '$(date -R)'"
    }
}

echo "Step 5: Installing Python packages to system Python..."
echo "Note: Installing to system Python (no virtual environment)."
echo "      Using --user flag to avoid permission issues (installs to ~/.local/lib/python3.x/site-packages)"
echo ""
if [ -f "requirements-pi.txt" ]; then
    # Check if OpenCV is available from apt (fast, pre-built) before installing pip packages
    if python3 -c "import cv2" 2>/dev/null; then
        echo "✓ OpenCV available from apt (skipping pip install - avoids slow build)"
    else
        echo "⚠ Warning: OpenCV not found from apt. pip requirements exclude it to avoid slow builds."
        echo "           Install with: sudo apt-get install -y python3-opencv"
    fi
    
    # Install with trusted hosts to avoid SSL issues (common on fresh Pi with wrong system clock)
    # Note: requirements-pi.txt does NOT include opencv-python-headless (use apt package instead)
    python3 -m pip install --user --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host www.piwheels.org -r requirements-pi.txt || {
        echo "Error: Failed to install Python packages. Check network connectivity and system clock."
        echo "       If system clock is wrong, run: sudo date -s '$(date -R)'"
        echo "       Then retry: python3 -m pip install --user -r requirements-pi.txt"
    }
    if [ -f "requirements-api.txt" ]; then
        echo "Installing API requirements (optional API server)..."
        python3 -m pip install --user --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host www.piwheels.org -r requirements-api.txt || {
            echo "⚠ Warning: API requirements installation failed."
            echo "         Check for version conflicts or network issues."
            echo "         API server is optional and can be installed separately if needed."
            echo "         Verify compatibility: python3 -m pip check"
        }
    fi
else
    echo "Warning: requirements file not found, installing manually..."
    python3 -m pip install --user "Flask>=2.0.0,<4.0.0"
    python3 -m pip install --user "Flask-SocketIO>=5.4.0,<6.0.0"
    python3 -m pip install --user "Werkzeug>=2.0.0,<4.0.0"
    python3 -m pip install --user "Jinja2>=3.0.0"
    python3 -m pip install --user "MarkupSafe>=2.0.0"
    python3 -m pip install --user "itsdangerous>=2.0.0"
    python3 -m pip install --user "gevent>=23.0.0,<25.0.0" "gevent-websocket>=0.10.1"
    python3 -m pip install --user "python-socketio>=5.14.0" "python-engineio>=4.9.0"
    python3 -m pip install --user "eventlet>=0.33.0,<1.0.0"
    # NOTE: OpenCV should be installed from apt (fast): sudo apt-get install -y python3-opencv
    # Do NOT install opencv-python-headless from pip (builds from source, takes hours)
    python3 -m pip install --user "numpy>=1.19.0,<2.0.0" "Pillow>=9.0.0"
    python3 -m pip install --user "PyYAML>=6.0"
fi

echo ""
echo "Step 6: Verifying installation..."
python3 -m pip list --user | grep -E "Flask|SocketIO|Werkzeug|Jinja2|MarkupSafe|numpy|Pillow|PyYAML" || echo "Warning: Some packages may not be installed correctly"

# Check OpenCV (should be from apt, not pip)
if python3 -c "import cv2; print('OpenCV', cv2.__version__, 'from', cv2.__file__)" 2>/dev/null; then
    echo "✓ OpenCV verified (installed from apt - fast, pre-built)"
else
    echo "⚠ Warning: OpenCV not found. Install with: sudo apt-get install -y python3-opencv"
fi

# Also check user-installed packages (with --user flag)
if [ -d "$HOME/.local/lib" ]; then
    echo ""
    echo "Checking user-installed packages (~/.local/lib):"
    python3 -m pip list --user | grep -E "Flask|SocketIO|Werkzeug|Jinja2|MarkupSafe|numpy|Pillow|PyYAML" || echo "Note: Packages may be in system site-packages"
fi

echo ""
echo "Step 7: Checking for legacy webapp processes..."
if pgrep -f "python.*pi_webapp.py" > /dev/null; then
    echo "⚠ Warning: Legacy webapp process detected. Stop it before running the new application:"
    echo "           pkill -f 'python.*pi_webapp.py'"
else
    echo "✓ No legacy webapp processes found"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. If legacy camera is not enabled, run: sudo raspi-config → Interface Options → Legacy Camera → Enable"
echo "  2. Reboot if you changed camera settings: sudo reboot"
echo "  3. After reboot, run the application:"
echo "     export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric"
echo "     export RIO_SIMULATION=false"
echo "     export RIO_DROPLET_ANALYSIS_ENABLED=true"
echo "     python main.py"
echo ""
echo "Or use the run.sh script after setting environment variables."
echo ""
echo "Note: Packages are installed to system Python. No virtual environment is used."
EOF

chmod +x "$DEPLOY_DIR/setup.sh"

# Create run script for Pi
cat > "$DEPLOY_DIR/run.sh" << 'EOF'
#!/bin/bash
# Run script for Raspberry Pi
# Uses system Python (no virtual environment)

cd "$(dirname "$0")"

# Set default environment variables if not set
export RIO_STROBE_CONTROL_MODE=${RIO_STROBE_CONTROL_MODE:-strobe-centric}
export RIO_SIMULATION=${RIO_SIMULATION:-false}
export RIO_DROPLET_ANALYSIS_ENABLED=${RIO_DROPLET_ANALYSIS_ENABLED:-true}
export RIO_FLOW_ENABLED=${RIO_FLOW_ENABLED:-false}
export RIO_HEATER_ENABLED=${RIO_HEATER_ENABLED:-false}

echo "Starting Rio microfluidics controller..."
echo "Control mode: $RIO_STROBE_CONTROL_MODE"
echo "Simulation: $RIO_SIMULATION"
echo "Droplet detection: $RIO_DROPLET_ANALYSIS_ENABLED"
echo ""

python main.py
EOF

chmod +x "$DEPLOY_DIR/run.sh"

# Copy README from original (it's generated in the script, but we'll keep the existing one)
# The README is already comprehensive, so we'll just note it's generated

echo ""
echo "Deployment package created in: $DEPLOY_DIR/"
echo ""
echo "To deploy to Raspberry Pi via SSH:"
echo "  ./scripts/deploy/deploy-to-pi.sh [pi-hostname]"
echo ""
echo "Package size: $(du -sh "$DEPLOY_DIR" | cut -f1)"
echo "Files: $(find "$DEPLOY_DIR" -type f | wc -l)"

