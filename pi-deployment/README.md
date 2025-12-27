# Rio Microfluidics Controller - Raspberry Pi Deployment

This is a minimal deployment package containing only the essential files needed to run the Rio microfluidics controller on Raspberry Pi.

## Quick Start

### 1. Setup (First time only)

```bash
./setup.sh
```

This will:
- Upgrade pip
- Install required packages to system Python
- Verify installation

**Note:** Packages are installed to system Python. No virtual environment is used.

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

### 3. Desktop Launcher (Optional)

To create a desktop launcher icon for easy access to the application:

1. **Copy the desktop file:**
   ```bash
   # For user-specific (recommended):
   cp omw.desktop ~/.local/share/applications/
   
   # Or for system-wide:
   sudo cp omw.desktop /usr/share/applications/
   ```

2. **Make it executable:**
   ```bash
   chmod +x ~/.local/share/applications/omw.desktop
   ```

3. **Refresh the desktop database:**
   ```bash
   update-desktop-database ~/.local/share/applications/
   # Or for system-wide:
   sudo update-desktop-database /usr/share/applications/
   ```

After these steps, you should see "Open Microfluidic Workstation" in your applications menu. The launcher will use `run.sh` if available (which sets proper environment variables), or fall back to directly running `python3 main.py`.

**Note:** The desktop launcher opens the application in a terminal window so you can see logs and output.

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
