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

# Path bootstrapper (needed for imports)
cp "$SOURCE_DIR/path_bootstrap.py" "$DEPLOY_DIR/"

# Configuration
cp "$SOURCE_DIR/config.py" "$DEPLOY_DIR/"
cp "$SOURCE_DIR/flow_control_modes.py" "$DEPLOY_DIR/"

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
# API requirements (optional API server on Pi)
cp "$SOURCE_DIR/requirements-api.txt" "$DEPLOY_DIR/" 2>/dev/null || true

# Create setup script for Pi
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
if [ -f "requirements-webapp-only-32bit.txt" ]; then
    # Check if OpenCV is available from apt (fast, pre-built) before installing pip packages
    if python3 -c "import cv2" 2>/dev/null; then
        echo "✓ OpenCV available from apt (skipping pip install - avoids slow build)"
    else
        echo "⚠ Warning: OpenCV not found from apt. pip requirements exclude it to avoid slow builds."
        echo "           Install with: sudo apt-get install -y python3-opencv"
    fi
    
    # Install with trusted hosts to avoid SSL issues (common on fresh Pi with wrong system clock)
    # Note: requirements-webapp-only-32bit.txt does NOT include opencv-python-headless (use apt package instead)
    python3 -m pip install --user --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host www.piwheels.org -r requirements-webapp-only-32bit.txt || {
        echo "Error: Failed to install Python packages. Check network connectivity and system clock."
        echo "       If system clock is wrong, run: sudo date -s '$(date -R)'"
        echo "       Then retry: python3 -m pip install --user -r requirements-webapp-only-32bit.txt"
    }
    if [ -f "requirements-api.txt" ]; then
        echo "Installing API requirements (optional API server)..."
        python3 -m pip install --user --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host www.piwheels.org -r requirements-api.txt || {
            echo "Warning: API requirements installation failed (known pydantic version conflict)."
            echo "         API server is optional and can be installed separately if needed."
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

# Create README for deployment
cat > "$DEPLOY_DIR/README.md" << 'EOF'
# pi-deployment/ — Raspberry Pi deployment bundle (generated)

**IMPORTANT:** This is for **Raspberry Pi deployment only**. For Mac/PC development setup, see `../software/README.md`.

This folder is a **minimal, runnable bundle** intended to be copied onto a Raspberry Pi for updates. It is generated from `software/` by `../create-pi-deployment.sh` (Linux/Mac) or `../create-pi-deployment.bat` (Windows) and should be treated as a **distribution output**, not a second source tree.

If you’re reviewing code logic, use this folder to understand *what is shipped to the Pi*, but treat `software/` as the source-of-truth for implementation.

## System Requirements

- **Raspberry Pi OS** (32-bit or 64-bit)
- **Python 3.8+** (system Python - do NOT use virtual environments on Pi)
- **System packages** should be installed via apt (see Hardware Requirements below)

## What’s in this folder (structure)

This folder intentionally mirrors the runtime-relevant parts of `software/`:

- `main.py`: runtime entry point (copied from `software/main.py`)
- `config.py`: shared constants (copied from `software/config.py`)
- `controllers/`, `drivers/`, `rio-webapp/`, `droplet-detection/`: the runtime code subset
- `configurations/`: example environment-variable “profiles” + quick reference docs
- `setup.sh`, `run.sh`: convenience scripts for first-time setup and running on the Pi
- `requirements-webapp-only-32bit.txt`: the pinned dependency set for this bundle

## Quick Start

**Important File Locations:**
- **Destination on Pi:** `~/rio-controller/` (or `/home/pi/rio-controller/`)
- **Application entry point:** `~/rio-controller/main.py`
- **Setup script:** `~/rio-controller/setup.sh` (first time only)
- **Run script:** `~/rio-controller/run.sh` (convenience script)
- **Packages installed to:** `~/.local/lib/python3.x/site-packages/` (user-level, no sudo)

### 1. Setup (first time only)

**IMPORTANT:** Packages are installed to **system Python** (no virtual environment). The setup script uses `--user` flag to avoid permission issues.

**Prerequisites:** Ensure you've copied all files from `pi-deployment/` to `~/rio-controller/` on your Pi (see [Copying Deployment to Pi](#copying-deployment-to-pi) below).

**Option A: Automated setup (if `setup.sh` is present)**
```bash
cd ~/rio-controller
./setup.sh
```

**Option B: Manual setup (always works)**
See manual installation steps below - this is equivalent and works even if `setup.sh` is missing.

This installs system packages (apt) and Python packages from `requirements-webapp-only-32bit.txt` using **system Python**. The script uses `python3 -m pip install --user` which installs packages to `~/.local/lib/python3.x/site-packages/` (no sudo required for Python packages).

**If `setup.sh` is missing or you prefer manual installation:** Install system packages and Python dependencies manually:

```bash
# Step 1: Install system packages (apt) - required for hardware and droplet detection
sudo apt-get update
sudo apt-get install -y python3-spidev python3-rpi.gpio python3-picamera python3-numpy python3-opencv
sudo apt-get install -y libatlas-base-dev libatlas3-base libblas3 liblapack3

# Step 2: Verify libcblas.so.3 is available (for droplet detection)
ldconfig -p | grep cblas  # Should show libcblas.so.3

# Step 3: Verify OpenCV from apt (fast, pre-built)
python3 -c "import cv2; print('OpenCV', cv2.__version__, 'installed from apt')"

# Step 4: Upgrade pip
python3 -m pip install --user --upgrade pip wheel

# Step 5: Install Python packages to user directory (no sudo needed)
# Note: requirements-webapp-only-32bit.txt does NOT include opencv-python-headless (use apt package)
python3 -m pip install --user -r requirements-webapp-only-32bit.txt

# Step 6: Verify installation
python3 -m pip list --user | grep -E "Flask|SocketIO|numpy|Pillow"
python3 -c "import cv2; print('✓ OpenCV verified')"  # Should be from apt

# Step 7: Clean GPIO state (if needed)
python3 - <<'PY'
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
try:
    GPIO.cleanup()
    GPIO.setmode(GPIO.BOARD)
except:
    pass
PY
```

**Troubleshooting permission issues:**
- If you get permission errors with `--user`, ensure `~/.local/bin` is in your PATH
- Alternatively, use `sudo python3 -m pip install -r requirements-webapp-only-32bit.txt` for system-wide installation (not recommended unless necessary)
- **DO NOT** create a virtual environment on the Pi - use system Python as shown above

### 2. Run

**Navigate to the deployment directory:**
```bash
cd ~/rio-controller
```

**Option 1: Use the run script (recommended)**
```bash
./run.sh
```

**Option 2: Run manually**
```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false      # Hide flow tab if not used
export RIO_HEATER_ENABLED=false    # Hide heater tab if not used
python main.py
```

**Access the web interface:**
- Open your browser to `http://raspberrypi.local:5000` (or `http://<PI_IP_ADDRESS>:5000`)

## Environment Variables

- `RIO_STROBE_CONTROL_MODE`: `strobe-centric` (32-bit, old firmware) or `camera-centric` (new firmware)
- `RIO_SIMULATION`: `false` for hardware operation
- `RIO_DROPLET_ANALYSIS_ENABLED`: `true` to enable droplet detection
- `RIO_PORT`: Port number (default: 5000)

## Configuration

See `configurations/` directory for example configuration files.

## Hardware Requirements

- Raspberry Pi OS (32-bit or 64-bit)
- **System Python packages** (installed via apt, not pip - fast, pre-built):
  - `spidev` (SPI communication)
  - `RPi.GPIO` (GPIO control)
  - `picamera` (for 32-bit) or `picamera2` (for 64-bit)
  - `python3-opencv` (image processing - **use apt, not pip** to avoid slow builds)
  - `python3-numpy` (required for OpenCV and droplet detection)
  - `libatlas-base-dev`, `libatlas3-base` (BLAS/LAPACK for droplet detection)

**Install missing hardware packages:**
```bash
# For 32-bit Raspberry Pi OS
sudo apt-get update
sudo apt-get install -y python3-spidev python3-rpi.gpio python3-picamera python3-opencv python3-numpy
sudo apt-get install -y libatlas-base-dev libatlas3-base libblas3 liblapack3

# For 64-bit Raspberry Pi OS
sudo apt-get update
sudo apt-get install -y python3-spidev python3-rpi.gpio python3-picamera2 python3-opencv python3-numpy
sudo apt-get install -y libatlas-base-dev libatlas3-base libblas3 liblapack3
```

**Verify hardware packages are installed:**
```bash
python3 -c "import spidev; import RPi.GPIO; print('Hardware packages: OK')"
python3 -c "import cv2; print('OpenCV', cv2.__version__, 'from apt')"
# For 32-bit:
python3 -c "import picamera; print('picamera: OK')"
# For 64-bit:
python3 -c "import picamera2; print('picamera2: OK')"
ldconfig -p | grep cblas  # Should show libcblas.so.3 for droplet detection
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

# If an old autostart webserver from a legacy install is running (e.g., pi_webapp.py), stop it first:
pkill -f "python.*pi_webapp.py"
ps aux | grep python  # verify no legacy webapp remains

# Or find and kill manually:
ps aux | grep "python.*main.py"
kill <PID>
```

### Start Application

**Navigate to the deployment directory:**
```bash
cd ~/rio-controller
```

**Option 1: Use the run script (recommended)**
```bash
./run.sh
```

**Option 2: Run manually**
```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_FLOW_ENABLED=false      # Hide flow tab if not used
export RIO_HEATER_ENABLED=false    # Hide heater tab if not used
python main.py
```

**Access the web interface:**
- Open your browser to `http://raspberrypi.local:5000` (or `http://<PI_IP_ADDRESS>:5000`)

### Copying Deployment to Pi

**On your Mac/PC (not on the Pi):** Generate the deployment bundle first, then copy it to your Raspberry Pi using one of the methods below.

#### Method 1: SSH/SCP (Network Connection)

**Linux/Mac:**
```bash
cd /path/to/rio-controller

# Recommended: use the safe wrapper (generates bundle + uses the correct rsync dest)
./deploy-to-pi.sh raspberrypi.local

# Or manual:
./create-pi-deployment.sh
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
  pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

**Windows:**
```cmd
cd C:\path\to\rio-controller

# Generate deployment bundle
create-pi-deployment.bat

# Copy to Pi using your preferred method:
# - WinSCP (GUI): Connect to pi@raspberrypi.local, copy pi-deployment/ contents to ~/rio-controller/
# - SCP (command line): scp -r pi-deployment\* pi@raspberrypi.local:~/rio-controller/
# - Or use rsync for Windows (via WSL or Cygwin)
```

#### Method 2: USB Stick (Physical Transfer)

**Step 1: Generate deployment bundle on Mac/PC**

**Linux/Mac:**
```bash
cd /path/to/rio-controller
./create-pi-deployment.sh
```

**Windows:**
```cmd
cd C:\path\to\rio-controller
create-pi-deployment.bat
```

**Step 2: Copy to USB stick**

- Plug in a USB stick (formatted as FAT32 or exFAT for compatibility)
- Copy the entire `pi-deployment/` folder to the USB stick root
- Safely eject the USB stick from your Mac/PC

**Step 3: Transfer to Raspberry Pi**

1. **Plug USB stick into Raspberry Pi**
2. **Mount USB stick** (if not auto-mounted):
   ```bash
   # Find USB device
   lsblk
   # Mount (replace sdX1 with your USB device, typically sda1 or sdb1)
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sdX1 /mnt/usb
   ```

3. **Copy files from USB stick to Pi**:
   ```bash
   # Create destination directory if it doesn't exist
   mkdir -p ~/rio-controller
   
   # Copy all files from USB stick
   cp -r /mnt/usb/pi-deployment/* ~/rio-controller/
   # Or if USB stick mounted to /media/pi/USB-STICK:
   cp -r /media/pi/USB-STICK/pi-deployment/* ~/rio-controller/
   ```

4. **Unmount USB stick** (when done):
   ```bash
   sudo umount /mnt/usb
   # Or if auto-mounted:
   sudo umount /media/pi/USB-STICK
   ```

5. **Navigate to deployment directory and continue with setup**:
   ```bash
   cd ~/rio-controller
   ./setup.sh  # First time only
   ./run.sh    # Or run manually
   ```

**Note:** The setup process is the same whether you use SSH or USB stick - once files are copied to `~/rio-controller/` on the Pi, follow the [Quick Start](#quick-start) instructions above.

**Important Notes:**
- `create-pi-deployment.sh` (Linux/Mac) or `create-pi-deployment.bat` (Windows) **regenerates** this folder. If you hand-edit files under `pi-deployment/`, those edits will be overwritten the next time the bundle is generated.
- **Avoid nested folders:** When copying, make sure to copy the *contents* of `pi-deployment/` to `~/rio-controller/`, not the folder itself. The destination should be `~/rio-controller/main.py`, not `~/rio-controller/pi-deployment/main.py`.
- If you see an empty folder on the Pi or nested `pi-deployment/`, you copied incorrectly. Fix by removing and re-copying with the correct path.

## Troubleshooting

### Network/DNS/SSL Issues (fresh Pi setup)
**Problem:** \`apt-get update\` or \`pip install\` fails with "Temporary failure resolving" or SSL certificate errors.

**Common causes:**
- System clock is incorrect (very common on fresh Pi - causes SSL cert verification to fail)
- No internet connection or DNS misconfigured

**Fix:**
\`\`\`bash
# Fix system clock (requires network):
sudo date -s "\$(date -R)"
# Or set manually if offline:
sudo date -s "2025-01-09 12:00:00"

# Retry installation
\`\`\`

### Dependencies (numpy/OpenCV)
- Pinned in requirements: \`opencv-python-headless<4.9\`, \`numpy<2.0\`. Prefer apt \`python3-numpy\` to avoid slow builds.

### Droplet detection: missing libcblas.so.3
Install ATLAS BLAS/LAPACK (provides libcblas.so.3):
\`\`\`bash
sudo apt-get update
sudo apt-get install -y libatlas-base-dev libatlas3-base libblas3 liblapack3
ldconfig -p | grep cblas  # confirm libcblas.so.3 is present
\`\`\`
**If packages not found:** Ensure Raspberry Pi Foundation apt repository is configured. Check:
\`\`\`bash
grep -r "raspberrypi.org" /etc/apt/sources.list /etc/apt/sources.list.d/
\`\`\`
If missing, add: \`deb http://archive.raspberrypi.org/debian/ bullseye main\` to \`/etc/apt/sources.list.d/raspberrypi.list\`

### Legacy camera (picamera)
- **Manual setup required:** Use \`sudo raspi-config\` → Interface Options → Legacy Camera → Enable; then reboot.
- Test: \`raspistill -v -o test.jpg\`
- Use \`python3-picamera\` (picamera2 not used on this setup).

### GPIO mode conflicts
- App uses BOARD numbering for GPIO. If another process set BCM, clean up:
\`\`\`bash
sudo pkill -f python
python3 - <<'PY'
import RPi.GPIO as GPIO
GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)
PY
\`\`\`

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
