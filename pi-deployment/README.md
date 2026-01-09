# pi-deployment/ — Raspberry Pi deployment bundle (generated)

**IMPORTANT:** This is for **Raspberry Pi deployment only**. For Mac/PC development setup, see `../software/README.md`.

This folder is a **minimal, runnable bundle** intended to be copied onto a Raspberry Pi for updates. It is generated from `software/` by `../create-pi-deployment.sh` (Linux/Mac) or `../create-pi-deployment.bat` (Windows) and should be treated as a **distribution output**, not a second source tree.

If you’re reviewing code logic, use this folder to understand *what is shipped to the Pi*, but treat `software/` as the source-of-truth for implementation.

## System Requirements

- **Raspberry Pi OS** (32-bit or 64-bit)
- **Python 3.8+** (system Python - we do not use virtual environments on Pi)
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

```bash
cd ~/rio-controller
./setup.sh
```

This installs from `requirements-webapp-only-32bit.txt` using **system Python** and verifies the install. The script uses `python3 -m pip install --user` which installs packages to `~/.local/lib/python3.x/site-packages/` (no sudo required).

**If `setup.sh` is missing:** Re-sync the deployment package from your Mac/PC (see "Sync Code" below) or install manually:

```bash
# Upgrade pip first
python3 -m pip install --user --upgrade pip wheel

# Install packages to user directory (no sudo needed)
python3 -m pip install --user -r requirements-webapp-only-32bit.txt

# Verify installation
python3 -m pip list --user | grep -E "Flask|SocketIO|opencv|numpy|Pillow"
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
- **System Python packages** (installed via apt, not pip):
  - `spidev` (SPI communication)
  - `RPi.GPIO` (GPIO control)
  - `picamera` (for 32-bit) or `picamera2` (for 64-bit)

**Install missing hardware packages:**
```bash
# For 32-bit Raspberry Pi OS
sudo apt-get update
sudo apt-get install -y python3-spidev python3-rpi.gpio python3-picamera

# For 64-bit Raspberry Pi OS
sudo apt-get update
sudo apt-get install -y python3-spidev python3-rpi.gpio python3-picamera2
```

**Verify hardware packages are installed:**
```bash
python3 -c "import spidev; import RPi.GPIO; print('Hardware packages: OK')"
# For 32-bit:
python3 -c "import picamera; print('picamera: OK')"
# For 64-bit:
python3 -c "import picamera2; print('picamera2: OK')"
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

**If an old autostart webserver from a legacy install is running** (often `/home/pi/webapp/pi_webapp.py` or another app name), stop it first so port 5000 is free:
```bash
ps aux | grep python       # find legacy webserver processes
pkill -f "python.*pi_webapp.py"   # adjust the pattern if the process name differs
```

If it respawns automatically, it’s likely managed by `systemd` or `cron`. Disable it:
```bash
sudo systemctl list-units | grep webapp   # find the unit name
sudo systemctl stop <unit>.service
sudo systemctl disable <unit>.service

crontab -l          # check user crontab for old start commands
sudo crontab -l     # check root crontab
```

### Start Application

```bash
cd ~/rio-controller
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

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


Note: `create-pi-deployment.sh` **regenerates** this folder. If you hand-edit files under `pi-deployment/`, those edits will be overwritten the next time the bundle is generated.

**Avoid nested folders:** do **not** rsync to `~/rio-controller/pi-deployment/` — that creates `~/rio-controller/pi-deployment/pi-deployment/...`.

If you only see an empty folder on the Pi, or you ended up with nested `pi-deployment/`, you likely ran `rsync` from the Pi instead of the Mac (or used the wrong destination path). Fix by removing the nested folder and re-syncing from your Mac/PC:

```bash
ssh pi@raspberrypi.local
rm -rf ~/rio-controller/pi-deployment
exit

cd /path/to/rio-controller
./deploy-to-pi.sh raspberrypi.local
```

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
