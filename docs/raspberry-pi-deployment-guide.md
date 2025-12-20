# Raspberry Pi Deployment Guide - Complete

This guide provides step-by-step instructions for deploying the Rio microfluidics controller from your Mac/PC to a Raspberry Pi. It covers the entire process from creating the deployment package to running the application.

---

## Overview

**Deployment Strategy:**
- Create minimal deployment package (540KB, ~52 files)
- Transfer to Pi via SSH/SCP
- Use virtual environment for webapp packages
- Keep hardware packages system-wide (spidev, RPi.GPIO, picamera)
- Isolated testing without affecting system Python

**Total Time:** ~15-20 minutes (mostly package installation on Pi)

---

## Prerequisites

### On Your Mac/PC

- Repository cloned locally
- Terminal access (bash/zsh)
- SSH/SCP access to Pi (built-in on macOS/Linux)

**No special requirements:**
- ❌ No Python environment needed on Mac
- ❌ No virtual environment needed
- ❌ No special dependencies

### On Raspberry Pi

- Raspberry Pi OS (32-bit or 64-bit) installed and running
- SSH enabled: `sudo systemctl enable ssh && sudo systemctl start ssh`
- Network connection (WiFi or Ethernet)
- User `pi` with password access
- System Python packages already installed:
  - `spidev` (SPI communication)
  - `RPi.GPIO` (GPIO control)
  - `picamera` (for 32-bit) or `picamera2` (for 64-bit)

**Check system packages on Pi:**
```bash
python3 -m pip list | grep -E "spidev|RPi.GPIO|picamera"
```

If missing:
```bash
sudo apt-get update
sudo apt-get install python3-spidev python3-rpi.gpio python3-picamera
```

---

## Step 1: Create Deployment Package (On Mac/PC)

**Location:** Repository root directory

```bash
cd /path/to/open-microfluidics-workstation

# Create deployment package
./create-pi-deployment.sh
```

**What this does:**
- Creates `pi-deployment/` directory
- Copies essential Python files (main.py, controllers, drivers, webapp)
- Excludes tests, simulation, documentation
- Creates setup and run scripts
- Adds README and requirements file

**Output:**
- `pi-deployment/` folder (~540KB, 52 files)
- Ready to transfer to Pi

**What's included:**
- ✅ Main application code
- ✅ Controllers and drivers
- ✅ Web application (Flask, templates, static files)
- ✅ Droplet detection module
- ✅ Configuration examples
- ✅ Setup and run scripts

**What's excluded:**
- ❌ Tests
- ❌ Simulation code
- ❌ Documentation
- ❌ Development files

---

## Step 2: Find Pi's Network Address

You need either the hostname or IP address of your Pi:

**Option A: Try hostname (if mDNS works):**
```bash
ping raspberrypi.local
```

**Option B: Find IP address:**
```bash
# Check your router's DHCP client list
# Or SSH in and run: hostname -I
# Or scan your network
```

**Common addresses:**
- Hostname: `raspberrypi.local`
- IP range: `192.168.x.x` or `10.0.x.x`

**Test connection:**
```bash
ssh pi@raspberrypi.local
# OR
ssh pi@192.168.1.XXX
```

---

## Step 3: Transfer Package to Pi (On Mac/PC)

**Location:** Repository root directory

**Option A: Automated Deployment (Recommended)**

```bash
./deploy-to-pi.sh raspberrypi.local
# OR with IP:
./deploy-to-pi.sh 192.168.1.XXX
```

You'll be prompted for the Pi's password (default: `raspberry` unless changed).

**What this does:**
1. Creates compressed tarball (`pi-deployment.tar.gz`)
2. Copies to Pi via SCP: `scp pi-deployment.tar.gz pi@raspberrypi.local:~/`
3. Extracts on Pi: `tar xzf ~/pi-deployment.tar.gz` in `~/rio-controller/`
4. Makes scripts executable

**Option B: Manual Deployment**

If automated script doesn't work:

```bash
# On Mac/PC
cd pi-deployment
tar czf ../pi-deployment.tar.gz .
scp ../pi-deployment.tar.gz pi@raspberrypi.local:~/

# Then SSH into Pi and extract
ssh pi@raspberrypi.local
mkdir -p ~/rio-controller
cd ~/rio-controller
tar xzf ~/pi-deployment.tar.gz
rm ~/pi-deployment.tar.gz
chmod +x setup.sh run.sh
```

---

## Step 4: Setup on Raspberry Pi

**SSH into Pi:**
```bash
ssh pi@raspberrypi.local
```

**Navigate to deployment directory:**
```bash
cd ~/rio-controller
```

**Run setup script:**
```bash
./setup.sh
```

**What setup.sh does:**
1. Creates Python virtual environment (`venv-rio/`)
2. Upgrades pip to latest version
3. Installs required packages:
   - Flask>=2.0.0,<4.0.0
   - Flask-SocketIO>=5.0.0,<6.0.0
   - Werkzeug>=2.0.0,<4.0.0
   - Jinja2>=3.0.0
   - MarkupSafe>=2.0.0
   - itsdangerous>=2.0.0
   - python-socketio>=5.0.0
   - eventlet>=0.33.0 (required for Flask-SocketIO)
   - opencv-python-headless>=4.5.0,<5.0.0 (faster on Pi)
   - PyYAML>=6.0

**Time:** ~5-10 minutes (depends on Pi speed and internet)

**Expected output:**
```
Rio Microfluidics Controller - Pi Setup
========================================

Step 1: Creating virtual environment...
Step 2: Activating virtual environment...
Step 3: Upgrading pip...
Step 4: Installing packages...
Step 5: Verifying installation...

Setup complete!
```

---

## Step 5: Configure Environment Variables

Edit `run.sh` or set manually:

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
export RIO_PORT=5000  # Optional, defaults to 5000
```

**Control modes:**
- `strobe-centric`: 32-bit only, old firmware, software trigger
- `camera-centric`: 32-bit or 64-bit, new firmware, hardware trigger

---

## Step 6: Run the Application

**Option A: Using run.sh (Recommended)**

```bash
cd ~/rio-controller
./run.sh
```

**Option B: Manual**

```bash
cd ~/rio-controller
source venv-rio/bin/activate
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

**Expected output:**
```
INFO - Initializing SPI communication...
INFO - Initializing hardware models...
INFO - Camera initialization complete
INFO - Starting Rio microfluidics controller on port 5000...
```

**Access web interface:**
- `http://raspberrypi.local:5000`
- Or `http://192.168.1.XXX:5000` (use Pi's IP)

---

## Directory Structure

### On Mac/PC:
```
open-microfluidics-workstation/
├── create-pi-deployment.sh      # Creates deployment package
├── deploy-to-pi.sh               # Automated deployment
└── pi-deployment/                # Created package (540KB)
    ├── main.py
    ├── config.py
    ├── setup.sh
    ├── run.sh
    ├── requirements-webapp-only-32bit.txt
    ├── controllers/
    ├── drivers/
    ├── droplet-detection/
    ├── rio-webapp/
    └── configurations/
```

### On Pi (after deployment):
```
~/rio-controller/
├── main.py
├── config.py
├── setup.sh
├── run.sh
├── venv-rio/                    # Virtual environment
│   ├── bin/
│   ├── lib/
│   └── ...
├── controllers/
├── drivers/
├── droplet-detection/
├── rio-webapp/
│   ├── controllers/
│   ├── static/
│   ├── templates/
│   └── routes.py
└── configurations/
```

---

## Troubleshooting

### Issue: SSH Connection Fails

**Symptoms:**
- `ssh: Could not resolve hostname raspberrypi.local`
- `Connection refused`

**Solutions:**
1. Check Pi is on same network
2. Use IP address instead: `ssh pi@192.168.1.XXX`
3. Verify SSH is enabled: `sudo systemctl status ssh`
4. Check firewall settings
5. Try direct connection (keyboard/mouse/display on Pi)

### Issue: Permission Denied

**Symptoms:**
- `Permission denied` when creating venv or running scripts

**Solutions:**
```bash
# Make sure you're in home directory or code directory
cd ~/rio-controller

# Make scripts executable
chmod +x setup.sh run.sh

# Create venv in your home directory if needed
cd ~
python3 -m venv venv-rio
```

### Issue: opencv-python Installation Hangs

**Symptoms:**
- Installation takes hours or gets stuck at "Building wheel for opencv-python"

**Solution:**
The deployment package now uses `opencv-python-headless` which has pre-built wheels. If you need to install manually:

```bash
pip install "opencv-python-headless>=4.5.0,<5.0.0"
```

This installs in minutes instead of hours.

### Issue: ModuleNotFoundError: No module named 'eventlet'

**Symptoms:**
- Error when running `python main.py`

**Solution:**
```bash
source venv-rio/bin/activate
pip install "eventlet>=0.33.0"
```

The deployment package now includes eventlet in requirements.

### Issue: ModuleNotFoundError for Hardware Packages

**Symptoms:**
- Errors about `spidev`, `RPi.GPIO`, or `picamera`

**Solution:**
These should be system-wide. Install if missing:
```bash
sudo apt-get install python3-spidev python3-rpi.gpio python3-picamera
```

Note: These are used from system Python, not from venv.

### Issue: Virtual Environment in Wrong Location

**Symptoms:**
- Venv created in `~/venv-rio` but code is in `~/rio-controller`

**Solutions:**

**Option A: Use venv from home directory:**
```bash
cd ~/rio-controller
source ~/venv-rio/bin/activate
python main.py
```

**Option B: Create venv in code directory (Recommended):**
```bash
cd ~/rio-controller
rm -rf venv-rio  # Remove old venv if exists
python3 -m venv venv-rio
source venv-rio/bin/activate
./setup.sh  # Or install packages manually
```

### Issue: Package Installation Fails

**Symptoms:**
- pip install errors, network errors

**Solutions:**
```bash
# Check internet connection
ping google.com

# Upgrade pip first
pip install --upgrade pip

# Try installing packages one by one to identify problem
pip install Flask
pip install Flask-SocketIO
# etc.
```

### Issue: Port Already in Use

**Symptoms:**
- `Address already in use` error

**Solution:**
```bash
# Find process using port 5000
sudo lsof -ti:5000 | xargs kill -9

# Or use different port
export RIO_PORT=5001
python main.py 5001
```

### Issue: Camera Not Detected

**Symptoms:**
- Camera initialization fails

**Solution:**
```bash
# Enable camera
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable

# Test camera (32-bit)
raspistill -o test.jpg

# Test camera (64-bit)
libcamera-hello
```

### Issue: SPI Not Working

**Symptoms:**
- Hardware communication errors

**Solution:**
```bash
# Enable SPI
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable

# Check SPI is enabled
lsmod | grep spi

# Verify user is in spi group
groups | grep spi
# If not:
sudo usermod -a -G spi,gpio pi
# Log out and back in
```

---

## Updating After Code Changes

When you make changes on Mac/PC and want to update the Pi:

1. **On Mac/PC - Recreate deployment:**
   ```bash
   cd /path/to/open-microfluidics-workstation
   ./create-pi-deployment.sh
   ```

2. **Deploy again (overwrites on Pi):**
   ```bash
   ./deploy-to-pi.sh raspberrypi.local
   ```

3. **On Pi - Reinstall packages if requirements changed:**
   ```bash
   cd ~/rio-controller
   source venv-rio/bin/activate
   pip install -r requirements-webapp-only-32bit.txt --upgrade
   ```

4. **Run again:**
   ```bash
   ./run.sh
   ```

---

## Quick Reference Commands

### On Mac/PC:
```bash
# Create deployment
./create-pi-deployment.sh

# Deploy to Pi
./deploy-to-pi.sh raspberrypi.local
```

### On Pi:
```bash
# Setup (first time only)
cd ~/rio-controller
./setup.sh

# Run
./run.sh

# Or manual
cd ~/rio-controller
source venv-rio/bin/activate
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

---

## Package Requirements Summary

### Installed in Virtual Environment (venv-rio):
- Flask>=2.0.0
- Flask-SocketIO>=5.0.0
- Werkzeug>=2.0.0
- Jinja2>=3.0.0
- MarkupSafe>=2.0.0
- itsdangerous>=2.0.0
- python-socketio>=5.0.0
- **eventlet>=0.33.0** (required!)
- **opencv-python-headless>=4.5.0,<5.0.0** (use headless version)
- PyYAML>=6.0

### Used from System Python:
- spidev (system-wide)
- RPi.GPIO (system-wide)
- picamera / picamera2 (system-wide)
- numpy (system-wide, compatible version)
- Pillow (system-wide, compatible version)
- eventlet (system-wide, but also in venv)

---

## Important Notes

1. **Virtual Environment**: All webapp packages are isolated in `venv-rio/`, keeping system Python untouched.

2. **Hardware Packages**: `spidev`, `RPi.GPIO`, and `picamera` are accessed from system Python even when venv is activated. This is by design - they need direct hardware access.

3. **opencv-python-headless**: Use the headless version on Pi - it has pre-built wheels and installs much faster than building from source.

4. **eventlet**: Required for Flask-SocketIO async support. Must be installed in venv.

5. **Resolution Configuration**: Camera resolution can be adjusted via the web interface UI. Config file values are initial defaults only.

6. **Framerate**: Automatically optimized from strobe timing. Use "Optimize" button in web interface.

---

## Verification Checklist

After deployment, verify:

- [ ] Deployment package created successfully
- [ ] Files transferred to Pi (`~/rio-controller/` exists)
- [ ] Virtual environment created (`~/rio-controller/venv-rio/` exists)
- [ ] All packages installed (check with `pip list`)
- [ ] eventlet installed (required!)
- [ ] opencv-python-headless installed (not regular opencv-python)
- [ ] Environment variables set correctly
- [ ] Application starts without errors
- [ ] Web interface accessible at `http://raspberrypi.local:5000`
- [ ] Hardware communication working (SPI, GPIO)

---

## Next Steps After Successful Deployment

1. **Test hardware connections:**
   - Camera feed working
   - Strobe responding
   - SPI communication stable

2. **Configure via web interface:**
   - Set strobe control mode (strobe-centric or camera-centric)
   - Adjust camera resolution
   - Configure droplet detection if enabled

3. **Set up autostart (optional):**
   - Create systemd service
   - Or add to `.bashrc` for manual start

4. **Document your specific configuration:**
   - Note which firmware version you have
   - Record any custom settings
   - Document network configuration

---

## Support

For issues not covered here:
- Check logs: Look for error messages in terminal output
- Verify hardware: Ensure SPI, GPIO, and camera are enabled
- Check network: Ensure Pi is accessible via SSH
- Review configuration: Verify environment variables are set correctly



