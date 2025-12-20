# Raspberry Pi Careful Update Guide

This guide helps you update your existing Raspberry Pi installation to the new webapp without breaking your current environment.

## Overview

**Strategy**: Use a Python virtual environment for webapp packages while keeping hardware packages (spidev, RPi.GPIO, picamera) system-wide since they're already at correct versions.

## Current Package Analysis

Your Pi already has:
- ✅ **Hardware packages** (correct versions):
  - `spidev==3.6` ✓
  - `RPi.GPIO==0.7.1` ✓
  - `picamera==1.13` ✓
  - `picamera2==0.3.12` ✓
  - `numpy==1.19.5` ✓ (compatible)
  - `Pillow==9.4.0` ✓ (compatible)
  - `eventlet==0.33.3` ✓

- ⚠️ **Webapp packages** (need updates):
  - `Flask==1.0.2` → needs `>=2.0.0,<4.0.0`
  - `Flask-SocketIO==4.3.2` → needs `>=5.0.0,<6.0.0`
  - `python-socketio==4.6.1` → needs `>=5.0.0`
  - `Werkzeug==0.14.1` → needs `>=2.0.0,<4.0.0`
  - `Jinja2==2.10` → needs `>=3.0.0`
  - `MarkupSafe==1.1.0` → needs `>=2.0.0`

- ❌ **Missing packages**:
  - `opencv-python-headless` (recommended) or `opencv-python` (for droplet detection)
  - `PyYAML` (for configuration files)

## Step-by-Step Update Process

### Step 0: Find Your Code Directory

First, find where your code is located:

```bash
# Check common locations
ls -la ~/ | grep -i microfluidics
ls -la ~/ | grep -i rio
ls -la ~/ | grep -i workstation

# Or search for main.py
find ~ -name "main.py" 2>/dev/null

# Or check if it's in Documents or other common locations
ls -la ~/Documents/ 2>/dev/null
ls -la ~/projects/ 2>/dev/null
```

Once you find the location (let's call it `CODE_DIR`), navigate there:

```bash
cd CODE_DIR/software
```

### Step 1: Create a Virtual Environment

**Important**: Create the venv in your home directory or in the software directory, NOT in system directories like `/opt`.

```bash
# Option A: Create venv in the software directory (recommended)
cd CODE_DIR/software
python3 -m venv venv-rio

# Option B: Create venv in your home directory (if CODE_DIR doesn't have write permissions)
cd ~
python3 -m venv venv-rio
```

### Step 2: Activate the Virtual Environment

```bash
# If you created it in CODE_DIR/software:
cd CODE_DIR/software
source venv-rio/bin/activate

# If you created it in your home directory:
source ~/venv-rio/bin/activate
```

You should see `(venv-rio)` at the beginning of your prompt.

### Step 3: Upgrade pip

```bash
pip install --upgrade pip
```

### Step 4: Install Updated Webapp Packages

If the requirements file exists in your code directory:

```bash
cd CODE_DIR/software
pip install -r requirements-webapp-only-32bit.txt
```

Or install manually:

```bash
# Core web framework (upgrades)
pip install "Flask>=2.0.0,<4.0.0"
pip install "Flask-SocketIO>=5.0.0,<6.0.0"
pip install "Werkzeug>=2.0.0,<4.0.0"
pip install "Jinja2>=3.0.0"
pip install "MarkupSafe>=2.0.0"
pip install "itsdangerous>=2.0.0"

# WebSocket support (upgrade)
pip install "python-socketio>=5.0.0"

# Missing packages
pip install "opencv-python-headless>=4.5.0,<5.0.0"  # Use headless version (faster installation on Pi)
pip install "PyYAML>=6.0"
```

**Note**: Hardware packages (spidev, RPi.GPIO, picamera, numpy, Pillow) will be available from the system Python since they're installed globally and at correct versions.

### Step 5: Verify Installation

```bash
pip list | grep -E "Flask|SocketIO|Werkzeug|Jinja2|MarkupSafe|opencv|PyYAML"
```

Expected output should show updated versions:
- Flask>=2.0.0
- Flask-SocketIO>=5.0.0
- python-socketio>=5.0.0
- Werkzeug>=2.0.0
- Jinja2>=3.0.0
- MarkupSafe>=2.0.0
- opencv-python
- PyYAML

### Step 6: Test the Application

```bash
# Make sure you're in the venv
source venv-rio/bin/activate  # Adjust path if needed

# Navigate to software directory
cd CODE_DIR/software

# Set environment variables
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric based on your firmware
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true

# Test run (will show errors if packages are missing)
python main.py
```

### Step 7: Create a Startup Script

Once you know your CODE_DIR location, create a startup script:

```bash
# Replace CODE_DIR with your actual path
cat > CODE_DIR/software/run-rio.sh << 'EOF'
#!/bin/bash
cd CODE_DIR/software  # Replace CODE_DIR with actual path
source venv-rio/bin/activate
export RIO_STROBE_CONTROL_MODE=strobe-centric  # Adjust as needed
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
EOF

chmod +x CODE_DIR/software/run-rio.sh
```

Or if venv is in home directory:

```bash
cat > CODE_DIR/software/run-rio.sh << 'EOF'
#!/bin/bash
cd CODE_DIR/software  # Replace CODE_DIR with actual path
source ~/venv-rio/bin/activate
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
EOF
```

## Troubleshooting

### Issue: Can't find the code directory

```bash
# Search for the repository
find ~ -type d -name "open-microfluidics-workstation" 2>/dev/null
find ~ -type d -name "*microfluidics*" 2>/dev/null
find ~ -type f -name "main.py" 2>/dev/null | head -1
```

### Issue: Permission denied when creating venv

Don't create venv in system directories like `/opt`, `/usr`, or `/etc`. Use:
- Your home directory: `~/venv-rio`
- The code directory: `CODE_DIR/software/venv-rio`
- A projects directory: `~/projects/venv-rio`

### Issue: Module not found errors for hardware packages

If you get errors about missing `spidev` or `RPi.GPIO`:

```bash
# These should already be installed system-wide, but if not:
sudo apt-get install python3-spidev python3-rpi.gpio
# Or via pip (system-wide, not in venv):
sudo pip3 install spidev RPi.GPIO
```

### Issue: picamera not found

```bash
# For 32-bit systems:
sudo apt-get install python3-picamera
# Or:
sudo pip3 install picamera
```

### Issue: Version conflicts

If you encounter version conflicts, check what's installed:

```bash
# In venv
pip list

# System-wide
pip3 list
```

### Issue: Permission errors with hardware

Make sure the Pi user has access:
```bash
sudo usermod -a -G spi,gpio pi
# Log out and back in for changes to take effect
```

## Rollback Plan

If something goes wrong:

1. **Deactivate venv**:
   ```bash
   deactivate
   ```

2. **Your old system packages are still there** - nothing was changed system-wide.

3. **Remove venv if needed**:
   ```bash
   rm -rf venv-rio  # or ~/venv-rio depending on where you created it
   ```

## Next Steps After Testing

Once everything works:

1. Update your desktop launcher (if you have one) to use the venv:
   ```ini
   Exec=bash -c "cd CODE_DIR/software && source venv-rio/bin/activate && python main.py"
   ```

2. Consider adding to your `.bashrc` (optional):
   ```bash
   alias rio='cd CODE_DIR/software && source venv-rio/bin/activate'
   ```

## Notes

- The virtual environment approach keeps your system Python untouched
- Hardware packages (spidev, RPi.GPIO, picamera) work from system Python even when using venv
- Only webapp packages are isolated in the venv
- This allows safe testing without risk to your existing setup
- Always create venv in directories you own (home directory or code directory), not system directories
