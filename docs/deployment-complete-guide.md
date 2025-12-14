# Complete Deployment Guide - Mac to Raspberry Pi

This guide provides step-by-step instructions for deploying the Rio microfluidics controller from your Mac to a Raspberry Pi.

## Overview

The deployment process:
1. **On Mac**: Creates a minimal package of essential code files
2. **Transfer**: Copies the package to the Pi via SSH
3. **On Pi**: Sets up a virtual environment and installs Python packages
4. **Run**: Starts the web application

## Prerequisites

### On Your Mac

- **Location**: You can run the deployment scripts from anywhere - they use relative paths
- **No special environment needed**: The scripts use standard bash commands
- **Requirements**:
  - `tar` (built-in on macOS)
  - `scp` (built-in, part of SSH)
  - `ssh` (built-in)
  - Terminal access

**You do NOT need:**
- Python environment on Mac
- Virtual environment activated
- Any specific directory
- The repository checked out in a particular location

### On Your Raspberry Pi

- Raspberry Pi OS (32-bit or 64-bit) installed and running
- SSH enabled (check: `sudo systemctl status ssh`)
- Network connection (WiFi or Ethernet)
- User `pi` exists with password access
- System Python packages already installed:
  - `spidev` (SPI communication)
  - `RPi.GPIO` (GPIO control)
  - `picamera` (for 32-bit) or `picamera2` (for 64-bit)

## Step-by-Step Process

### Step 1: Prepare Deployment Package (On Mac)

**Location**: Repository root directory

```bash
# Navigate to repository root (where you have the code)
cd /path/to/open-microfluidics-workstation

# Create the deployment package
./create-pi-deployment.sh
```

This creates a `pi-deployment/` directory containing:
- All essential Python code files
- Configuration examples
- Setup and run scripts
- Requirements file
- README

**What's included:**
- ✅ Main application (`main.py`, `config.py`)
- ✅ Controllers (hardware control logic)
- ✅ Drivers (hardware communication)
- ✅ Droplet detection module
- ✅ Web application (Flask, templates, static files)
- ✅ Configuration examples

**What's excluded:**
- ❌ Tests
- ❌ Simulation code
- ❌ Documentation (stays on Mac)
- ❌ Development files
- ❌ Python cache files

**Package size**: ~540KB, ~52 files

### Step 2: Find Your Pi's Address

You need either:
- **Hostname**: Usually `raspberrypi.local` (if mDNS is working)
- **IP Address**: `192.168.1.XXX` (check your router or use `ping raspberrypi.local`)

**Test connection**:
```bash
# Try hostname first
ping raspberrypi.local

# If that doesn't work, find the IP
arp -a | grep raspberrypi
# Or check your router's DHCP client list
```

### Step 3: Deploy to Pi (On Mac)

**Option A: Automated Deployment (Recommended)**

From repository root:

```bash
./deploy-to-pi.sh raspberrypi.local
# OR if you know the IP:
./deploy-to-pi.sh 192.168.1.100
```

You'll be prompted for the Pi's password (default: `raspberry` unless you changed it).

This script:
1. Creates a compressed tarball
2. Copies it to the Pi via SCP
3. Extracts it to `~/rio-controller/` on the Pi
4. Makes scripts executable

**Option B: Manual Deployment**

If the automated script doesn't work:

```bash
# On Mac - create tarball
cd pi-deployment
tar czf ../pi-deployment.tar.gz .

# Copy to Pi
scp ../pi-deployment.tar.gz pi@raspberrypi.local:~/

# Then SSH into Pi and extract
ssh pi@raspberrypi.local
mkdir -p ~/rio-controller
cd ~/rio-controller
tar xzf ~/pi-deployment.tar.gz
chmod +x setup.sh run.sh
```

### Step 4: Setup on Pi (On Pi via SSH)

```bash
# SSH into the Pi
ssh pi@raspberrypi.local

# Navigate to deployment directory
cd ~/rio-controller

# Run setup script (first time only)
./setup.sh
```

**What setup.sh does:**
1. Creates Python virtual environment (`venv-rio/`)
2. Activates the virtual environment
3. Upgrades pip
4. Installs required packages:
   - Flask, Flask-SocketIO (updated versions)
   - opencv-python (for droplet detection)
   - PyYAML (for configuration)
   - Other dependencies

**Time**: ~5-10 minutes depending on Pi speed and internet connection

**Note**: Hardware packages (spidev, RPi.GPIO, picamera) are used from system Python - they're already installed.

### Step 5: Configure Environment (On Pi)

Edit `run.sh` to set your environment variables, or set them manually:

```bash
# Edit run.sh to change defaults, or set manually:
export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
```

### Step 6: Run the Application (On Pi)

```bash
# Simple way (uses defaults from run.sh)
./run.sh

# Or manually
source venv-rio/bin/activate
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

The web interface will be available at:
- `http://raspberrypi.local:5000` (or `http://192.168.1.XXX:5000`)

## Directory Structure

### On Mac:
```
open-microfluidics-workstation/
├── create-pi-deployment.sh      # Creates deployment package
├── deploy-to-pi.sh               # Automated deployment
├── pi-deployment/                # Created package (540KB)
│   ├── main.py
│   ├── config.py
│   ├── setup.sh
│   ├── run.sh
│   ├── requirements-webapp-only-32bit.txt
│   ├── controllers/
│   ├── drivers/
│   ├── droplet-detection/
│   ├── rio-webapp/
│   └── configurations/
└── software/                     # Full source code
```

### On Pi (after deployment):
```
~/rio-controller/
├── main.py
├── config.py
├── setup.sh
├── run.sh
├── venv-rio/                    # Virtual environment (created by setup.sh)
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

## What Happens During Deployment

### 1. Package Creation (`create-pi-deployment.sh`)

- Scans `software/` directory
- Copies essential Python files
- Excludes tests, simulation, cache files
- Creates setup and run scripts
- Adds README and documentation
- **Output**: `pi-deployment/` directory

### 2. Transfer (`deploy-to-pi.sh` or manual)

- Creates compressed tarball (`pi-deployment.tar.gz`)
- Copies via SCP to Pi's home directory
- Extracts on Pi to `~/rio-controller/`
- Makes scripts executable
- **Result**: All files on Pi, ready for setup

### 3. Setup (`setup.sh` on Pi)

- Creates isolated Python virtual environment
- Installs updated webapp packages (Flask, etc.)
- Keeps system Python untouched
- Verifies installation
- **Result**: Ready to run

### 4. Running (`run.sh` or `python main.py`)

- Activates virtual environment
- Uses system hardware packages (spidev, RPi.GPIO, picamera)
- Uses venv webapp packages (Flask, opencv, etc.)
- Starts Flask web server
- **Result**: Web interface accessible on network

## Troubleshooting

### Mac Side Issues

**Script permission denied:**
```bash
chmod +x create-pi-deployment.sh deploy-to-pi.sh
```

**Can't find repository:**
```bash
# Find where you cloned it
find ~ -name "open-microfluidics-workstation" -type d
cd /path/to/open-microfluidics-workstation
```

**SSH connection fails:**
- Check Pi is on same network
- Verify SSH is enabled on Pi: `sudo systemctl status ssh`
- Try IP address instead of hostname
- Check firewall settings

### Pi Side Issues

**Permission denied:**
```bash
chmod +x setup.sh run.sh
```

**Virtual environment creation fails:**
```bash
# Ensure you're in the right directory
cd ~/rio-controller
python3 -m venv venv-rio
```

**Package installation fails:**
```bash
# Check internet connection
ping google.com

# Upgrade pip
source venv-rio/bin/activate
pip install --upgrade pip

# Try installing packages one by one
pip install Flask
```

**Hardware packages missing:**
```bash
sudo apt-get update
sudo apt-get install python3-spidev python3-rpi.gpio python3-picamera
```

**Module not found errors:**
- Check if virtual environment is activated: `which python` should show `venv-rio`
- Verify all Python files were copied: `ls -la ~/rio-controller/controllers/`

## Updating After Changes

When you make code changes on Mac:

1. **Recreate deployment package:**
   ```bash
   cd /path/to/open-microfluidics-workstation
   ./create-pi-deployment.sh
   ```

2. **Deploy again** (overwrites on Pi):
   ```bash
   ./deploy-to-pi.sh raspberrypi.local
   ```

3. **On Pi, reinstall if requirements changed:**
   ```bash
   cd ~/rio-controller
   source venv-rio/bin/activate
   pip install -r requirements-webapp-only-32bit.txt
   ```

## Security Notes

- Default Pi password is `raspberry` - change it if exposed to internet
- The web app binds to `0.0.0.0:5000` - accessible on local network
- Consider firewall rules if needed
- SSH keys recommended for production use

## Next Steps

After successful deployment:
1. Access web interface at `http://raspberrypi.local:5000`
2. Configure strobe control mode (strobe-centric or camera-centric)
3. Test camera and hardware connections
4. Set up desktop launcher if desired
5. Configure autostart if needed (systemd service)
