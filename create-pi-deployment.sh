#!/bin/bash
# Create a minimal deployment package for Raspberry Pi
# Excludes tests, simulation, documentation, and development files

set -e

DEPLOY_DIR="pi-deployment"
SOURCE_DIR="software"

echo "Creating Raspberry Pi deployment package..."

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

# Configurations
cp -r "$SOURCE_DIR/configurations" "$DEPLOY_DIR/"

# Requirements file
cp "$SOURCE_DIR/requirements-webapp-only-32bit.txt" "$DEPLOY_DIR/"

# Create setup script for Pi
cat > "$DEPLOY_DIR/setup.sh" << 'EOF'
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

# Create README for deployment
cat > "$DEPLOY_DIR/README.md" << 'EOF'
# pi-deployment/ — Raspberry Pi deployment bundle (generated)

This folder is a **minimal, runnable bundle** intended to be copied onto a Raspberry Pi for updates. It is generated from `software/` by `../create-pi-deployment.sh` and should be treated as a **distribution output**, not a second source tree.

If you’re reviewing code logic, use this folder to understand *what is shipped to the Pi*, but treat `software/` as the source-of-truth for implementation.

## What’s in this folder (structure)

This folder intentionally mirrors the runtime-relevant parts of `software/`:

- `main.py`: runtime entry point (copied from `software/main.py`)
- `config.py`: shared constants (copied from `software/config.py`)
- `controllers/`, `drivers/`, `rio-webapp/`, `droplet-detection/`: the runtime code subset
- `configurations/`: example environment-variable “profiles” + quick reference docs
- `setup.sh`, `run.sh`: convenience scripts for first-time setup and running on the Pi
- `requirements-webapp-only-32bit.txt`: the pinned dependency set for this bundle

## Quick Start

### 1. Setup (first time only)

```bash
./setup.sh
```

This installs from `requirements-webapp-only-32bit.txt` using system Python and verifies the install. If `setup.sh` is missing, re-sync the deployment package from your Mac (see “Sync Code” below) or install directly with:
```bash
python3 -m pip install --upgrade pip wheel
pip install -r requirements-webapp-only-32bit.txt
```
Packages are installed to system Python (no virtualenv).

### 2. Run

```bash
./run.sh
```

Or manually:

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false      # Hide flow tab if not used
export RIO_HEATER_ENABLED=false    # Hide heater tab if not used
python main.py
```

## Environment Variables

- `RIO_STROBE_CONTROL_MODE`: `strobe-centric` (32-bit, old firmware) or `camera-centric` (new firmware)
- `RIO_SIMULATION`: `false` for hardware operation
- `RIO_DROPLET_ANALYSIS_ENABLED`: `true` to enable droplet detection
- `RIO_PORT`: Port number (default: 5000)

## Configuration

See `configurations/` directory for example configuration files.

## Hardware Requirements

- Raspberry Pi OS (32-bit or 64-bit)
- System packages should already be installed:
  - spidev (SPI communication)
  - RPi.GPIO (GPIO control)
  - picamera (for 32-bit) or picamera2 (for 64-bit)

If hardware packages are missing:
```bash
sudo apt-get install python3-spidev python3-rpi.gpio python3-picamera
```

## Development Workflow

### Connect to Pi

```bash
ssh pi@raspberrypi.local
# Or: ssh pi@<IP_ADDRESS>
```

### Stop Application

```bash
# Stop running instance
pkill -f "python.*main.py"

# Or find and kill manually:
ps aux | grep "python.*main.py"
kill <PID>
```

### Start Application

```bash
cd ~/rio-controller
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

### Sync Code (from Mac/PC)

```bash
cd /Users/twenzel/Documents/GitHub/rio-controller
./create-pi-deployment.sh
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

Note: `create-pi-deployment.sh` **regenerates** this folder. If you hand-edit files under `pi-deployment/`, those edits will be overwritten the next time the bundle is generated.

If you only see an empty folder on the Pi, you likely ran `rsync` from the Pi instead of the Mac. Re-run the above commands from your Mac so `setup.sh`, `run.sh`, and the requirements file are copied.

## Troubleshooting

### Enable Debug Logging

For troubleshooting, you can enable more verbose logging by setting the `RIO_LOG_LEVEL` environment variable:

```bash
export RIO_LOG_LEVEL=DEBUG  # Most verbose - shows all debug messages
export RIO_LOG_LEVEL=INFO   # Shows informational messages (recommended for troubleshooting)
export RIO_LOG_LEVEL=WARNING  # Default - only warnings and errors (production mode)
export RIO_LOG_LEVEL=ERROR    # Only errors
```

**Log Levels:**
- **DEBUG**: All messages including detailed debug info (high volume, use only when troubleshooting)
- **INFO**: Important operational messages (recommended for troubleshooting - shows strobe events, camera status, etc.)
- **WARNING**: Warnings and errors only (default, minimal bandwidth/IO overhead)
- **ERROR**: Errors only (minimal logging)

**Example with debug logging:**
```bash
export RIO_LOG_LEVEL=INFO
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

**Note:** Logging doesn't consume significant bandwidth when set to WARNING or ERROR. DEBUG and INFO levels are designed for troubleshooting and provide detailed operational information without impacting performance when disabled.

### Application Hangs on Startup

If `python main.py` produces no output and hangs:

**Check for multiple Socket.IO installations:**
```bash
python3 -c "import socketio; print(f'Version: {socketio.__version__}'); print(f'Location: {socketio.__file__}')"
pip list | grep socketio
```

**Fix:** Uninstall from all locations:
```bash
pip uninstall Flask-SocketIO python-socketio python-engineio -y
sudo pip uninstall Flask-SocketIO python-socketio python-engineio -y 2>/dev/null || true
pip install python-engineio==3.13.2
pip install Flask-SocketIO==4.3.2
```

**If still hanging:**
```bash
sudo lsof -i :5000  # Check if port is in use
python3 -v main.py 2>&1 | head -50  # Verbose mode to see where it hangs
```

See the full documentation in the main repository for detailed troubleshooting steps.
EOF

# Create .gitignore for deployment (if it gets version controlled)
cat > "$DEPLOY_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv-rio/
*.egg-info/
dist/
build/

# Snapshots
home/pi/snapshots/*.jpg

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF

# Create deployment info file
cat > "$DEPLOY_DIR/DEPLOYMENT_INFO.txt" << EOF
Rio Microfluidics Controller - Deployment Package
Created: $(date)
Source: open-microfluidics-workstation/software
Branch: strobe-rewrite

This package contains:
- Main application code (main.py, config.py)
- Controllers (hardware control logic)
- Drivers (hardware communication)
- Droplet detection module
- Web application (Flask, templates, static files)
- Configuration examples

Excluded:
- Tests
- Simulation code
- Documentation (see main repository)
- Development files
- Python cache files

Size: $(du -sh "$DEPLOY_DIR" | cut -f1)
EOF

echo ""
echo "Deployment package created in: $DEPLOY_DIR/"
echo ""
echo "To deploy to Raspberry Pi via SSH:"
echo ""
echo "  # From your Mac/PC:"
echo "  cd $DEPLOY_DIR"
echo "  tar czf ../pi-deployment.tar.gz ."
echo "  scp ../pi-deployment.tar.gz pi@raspberrypi.local:~/"
echo ""
echo "  # Then on the Pi:"
echo "  cd ~"
echo "  mkdir -p rio-controller"
echo "  cd rio-controller"
echo "  tar xzf ~/pi-deployment.tar.gz"
echo "  ./setup.sh"
echo ""
echo "Package size: $(du -sh "$DEPLOY_DIR" | cut -f1)"
echo "Files: $(find "$DEPLOY_DIR" -type f | wc -l)"
