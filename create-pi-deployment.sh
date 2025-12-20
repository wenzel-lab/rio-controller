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
# Setup script for Raspberry Pi
# Run this after copying the deployment package to the Pi

set -e

echo "Rio Microfluidics Controller - Pi Setup"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Please run this script from the deployment directory."
    exit 1
fi

echo "Step 1: Creating virtual environment..."
python3 -m venv venv-rio

echo "Step 2: Activating virtual environment..."
source venv-rio/bin/activate

echo "Step 3: Upgrading pip..."
pip install --upgrade pip

echo "Step 4: Installing packages..."
if [ -f "requirements-webapp-only-32bit.txt" ]; then
    pip install -r requirements-webapp-only-32bit.txt
else
    echo "Warning: requirements file not found, installing manually..."
    pip install "Flask>=2.0.0,<4.0.0"
    pip install "Flask-SocketIO>=5.0.0,<6.0.0"
    pip install "Werkzeug>=2.0.0,<4.0.0"
    pip install "Jinja2>=3.0.0"
    pip install "MarkupSafe>=2.0.0"
    pip install "itsdangerous>=2.0.0"
    pip install "python-socketio>=5.0.0"
    pip install "eventlet>=0.33.0"
    pip install "opencv-python-headless>=4.5.0,<5.0.0"
    pip install "PyYAML>=6.0"
fi

echo ""
echo "Step 5: Verifying installation..."
pip list | grep -E "Flask|SocketIO|Werkzeug|Jinja2|MarkupSafe|opencv|PyYAML" || echo "Warning: Some packages may not be installed correctly"

echo ""
echo "Setup complete!"
echo ""
echo "To run the application:"
echo "  1. source venv-rio/bin/activate"
echo "  2. export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric"
echo "  3. export RIO_SIMULATION=false"
echo "  4. export RIO_DROPLET_ANALYSIS_ENABLED=true"
echo "  5. python main.py"
echo ""
echo "Or use the run.sh script after setting environment variables."
EOF

chmod +x "$DEPLOY_DIR/setup.sh"

# Create run script for Pi
cat > "$DEPLOY_DIR/run.sh" << 'EOF'
#!/bin/bash
# Run script for Raspberry Pi
# Activates venv and runs the application

cd "$(dirname "$0")"

if [ ! -d "venv-rio" ]; then
    echo "Error: Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

source venv-rio/bin/activate

# Set default environment variables if not set
export RIO_STROBE_CONTROL_MODE=${RIO_STROBE_CONTROL_MODE:-strobe-centric}
export RIO_SIMULATION=${RIO_SIMULATION:-false}
export RIO_DROPLET_ANALYSIS_ENABLED=${RIO_DROPLET_ANALYSIS_ENABLED:-true}

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
# Rio Microfluidics Controller - Raspberry Pi Deployment

This is a minimal deployment package containing only the essential files needed to run the Rio microfluidics controller on Raspberry Pi.

## Quick Start

### 1. Setup (First time only)

```bash
./setup.sh
```

This will:
- Create a Python virtual environment (`venv-rio`)
- Install required packages
- Verify installation

### 2. Run

```bash
./run.sh
```

Or manually:

```bash
source venv-rio/bin/activate
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
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

## Troubleshooting

See the full documentation in the main repository for troubleshooting steps.
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
