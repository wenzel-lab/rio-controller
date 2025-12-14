# Raspberry Pi Deployment Guide

This guide explains how to deploy the Rio microfluidics controller to a Raspberry Pi without copying the entire repository.

## Quick Deployment

### Step 1: Create Deployment Package

From the repository root:

```bash
./create-pi-deployment.sh
```

This creates a `pi-deployment/` directory containing only essential files (no tests, simulation, or documentation).

### Step 2: Deploy to Raspberry Pi

**Option A: Automated Deployment (Recommended)**

```bash
./deploy-to-pi.sh [pi-hostname-or-ip]
```

Example:
```bash
./deploy-to-pi.sh raspberrypi.local
# or
./deploy-to-pi.sh 192.168.1.100
```

This will:
1. Create a tarball of the deployment package
2. Copy it to the Pi via SCP
3. Extract it on the Pi to `~/rio-controller/`
4. Make scripts executable

**Option B: Manual Deployment**

```bash
# On your Mac/PC
cd pi-deployment
tar czf ../pi-deployment.tar.gz .
scp ../pi-deployment.tar.gz pi@raspberrypi.local:~/

# Then on the Pi (via SSH)
ssh pi@raspberrypi.local
mkdir -p ~/rio-controller
cd ~/rio-controller
tar xzf ~/pi-deployment.tar.gz
rm ~/pi-deployment.tar.gz
chmod +x setup.sh run.sh
```

### Step 3: Setup on Raspberry Pi

SSH into the Pi:

```bash
ssh pi@raspberrypi.local
cd ~/rio-controller
```

Run the setup script:

```bash
./setup.sh
```

This will:
- Create a Python virtual environment (`venv-rio`)
- Install required packages
- Verify installation

### Step 4: Run the Application

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

## What Gets Deployed

The deployment package includes:

- ✅ **Essential code**:
  - `main.py` - Application entry point
  - `config.py` - Configuration constants
  - `controllers/` - Hardware control logic
  - `drivers/` - Hardware communication
  - `droplet-detection/` - Droplet analysis (excluding tests)
  - `rio-webapp/` - Web interface (Flask, templates, static files)
  - `configurations/` - Configuration examples

- ✅ **Setup files**:
  - `setup.sh` - Initial setup script
  - `run.sh` - Application launcher
  - `requirements-webapp-only-32bit.txt` - Package requirements
  - `README.md` - Quick reference

- ❌ **Excluded**:
  - Tests (`tests/`)
  - Simulation code (`simulation/`)
  - Documentation (`docs/`)
  - Development files (`.flake8`, `pyproject.toml`)
  - Python cache files (`__pycache__/`, `*.pyc`)

## Directory Structure on Pi

After deployment:

```
~/rio-controller/
├── main.py
├── config.py
├── setup.sh
├── run.sh
├── requirements-webapp-only-32bit.txt
├── README.md
├── controllers/
├── drivers/
├── droplet-detection/
├── rio-webapp/
│   ├── controllers/
│   ├── static/
│   ├── templates/
│   └── routes.py
├── configurations/
└── venv-rio/          # Created by setup.sh
```

## Environment Variables

Set these before running (or edit `run.sh`):

- `RIO_STROBE_CONTROL_MODE`: `strobe-centric` (32-bit, old firmware) or `camera-centric` (new firmware)
- `RIO_SIMULATION`: `false` for hardware operation
- `RIO_DROPLET_ANALYSIS_ENABLED`: `true` to enable droplet detection
- `RIO_PORT`: Port number (default: 5000)

## Troubleshooting

### SSH Connection Issues

If `raspberrypi.local` doesn't work:
- Use the Pi's IP address: `192.168.1.XXX`
- Find IP with: `ping raspberrypi.local` or check your router
- Make sure Pi is on the same network

### Permission Denied

```bash
# Make sure scripts are executable
chmod +x setup.sh run.sh
```

### Package Installation Fails

If packages fail to install:
- Check internet connection on Pi
- Try upgrading pip: `pip install --upgrade pip`
- Check Python version: `python3 --version` (should be 3.7+)

### Hardware Packages Missing

If you get errors about `spidev` or `RPi.GPIO`:

```bash
sudo apt-get update
sudo apt-get install python3-spidev python3-rpi.gpio python3-picamera
```

### Virtual Environment Issues

If venv activation fails:
```bash
# Recreate venv
rm -rf venv-rio
python3 -m venv venv-rio
source venv-rio/bin/activate
pip install --upgrade pip
pip install -r requirements-webapp-only-32bit.txt
```

## Updating the Deployment

To update after making changes:

1. **On your Mac/PC**: Recreate the deployment package
   ```bash
   ./create-pi-deployment.sh
   ```

2. **Deploy again** (this will overwrite on Pi):
   ```bash
   ./deploy-to-pi.sh raspberrypi.local
   ```

3. **On the Pi**: Reinstall packages if requirements changed
   ```bash
   cd ~/rio-controller
   source venv-rio/bin/activate
   pip install -r requirements-webapp-only-32bit.txt
   ```

## Alternative: Direct File Copy

If you prefer not to use tarballs, you can use `rsync`:

```bash
rsync -avz --exclude '__pycache__' --exclude '*.pyc' \
  pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

## Notes

- The virtual environment is created in `~/rio-controller/venv-rio/`
- All code runs from `~/rio-controller/`
- Hardware packages (spidev, RPi.GPIO, picamera) must be installed system-wide
- Webapp packages are isolated in the virtual environment
- Snapshots are saved to `~/rio-controller/home/pi/snapshots/` (will be created automatically)
