# Raspberry Pi Software Update Guide

**Branch:** `strobe-rewrite`  
**Target:** Raspberry Pi with existing 32-bit system  
**Date:** Migration guide for testing new code with legacy firmware

---

## Overview

This guide explains how to update your Raspberry Pi system from the old installation (master branch) to the new `strobe-rewrite` branch while maintaining compatibility with existing firmware. The new code includes a configuration option to switch between:

**For careful updates without breaking existing setup**: See [Careful Update Guide](raspberry-pi-careful-update-guide.md) for using a virtual environment approach.

1. **Strobe-centric mode**: Compatible with firmware that uses software trigger mode. Works on 32-bit Raspberry Pi OS only (requires picamera package). This mode works perfectly fine if you already have a working 32-bit system.

2. **Camera-centric mode**: Uses new firmware with hardware trigger support. Provides better synchronization. Requires new strobe chip firmware with hardware trigger capability.

---

## Prerequisites

- Raspberry Pi running 32-bit or 64-bit Raspberry Pi OS (Bullseye or later)
- Existing working installation from master branch (if updating existing system)
- Internet connection
- Access to Raspberry Pi (via SSH over network, or directly with keyboard/mouse/display)

**Note:** Connection method (SSH vs direct) doesn't matter - use whichever is convenient for you.

---

## New Packages Required

The new codebase requires additional packages compared to the old installation. Here's what needs to be added:

### New Dependencies

1. **PyYAML** (>=6.0)
   - Purpose: Configuration file support
   - Install: `pip install PyYAML>=6.0`

2. **numpy** (>=1.19.0,<2.0.0 for 32-bit)
   - Purpose: Droplet detection and image processing
   - Install: `pip install "numpy>=1.19.0,<2.0.0"`

3. **opencv-python-headless** (>=4.5.0,<5.0.0) - **Recommended for Pi**
   - Purpose: Droplet detection algorithms
   - Install: `pip install "opencv-python-headless>=4.5.0,<5.0.0"`
   - Note: Use headless version on Raspberry Pi - it has pre-built wheels and installs much faster (minutes vs hours). Regular `opencv-python` works but compiles from source.

4. **python-socketio** (>=5.0.0)
   - Purpose: Enhanced WebSocket support
   - Install: `pip install python-socketio>=5.0.0`

### Updated Dependencies

The following packages will be upgraded automatically when installing new requirements:

- **Flask**: 1.0.2 → >=2.0.0,<4.0.0
- **Flask-SocketIO**: 4.3.2 → >=5.0.0,<6.0.0
- **Werkzeug**: 0.14.1 → >=2.0.0,<4.0.0
- **Jinja2**: 2.10 → >=3.0.0
- **MarkupSafe**: 1.1.0 → >=2.0.0
- **itsdangerous**: 0.24 → >=2.0.0

**Note:** Existing packages (spidev, RPi.GPIO, picamera, Pillow, eventlet) remain at the same versions.

---

## Update Procedure

### Step 1: Backup Your Current Installation {pagestep}

Before making any changes, create a backup:

```bash
# Backup the current webapp directory (adjust path as needed)
sudo cp -r /home/pi/webapp /home/pi/webapp_backup

# Backup requirements if you have a custom one
cp /home/pi/requirements.txt /home/pi/requirements.txt.backup 2>/dev/null || true
```

### Step 2: Prepare Python Environment {pagestep}

On Raspberry Pi, you can use the system Python directly (no virtual environment needed for hardware operation). Virtual environments are mainly used for development/testing on Mac/PC.

If you have a desktop launcher or startup script, you may need to update it to set environment variables (see Step 5).

### Step 3: Update Code from Repository {pagestep}

```bash
# Navigate to the repository directory
cd /home/pi/open-microfluidics-workstation  # Adjust path as needed

# Switch to the strobe-rewrite branch
git fetch origin
git checkout strobe-rewrite
git pull origin strobe-rewrite
```

### Step 4: Install New Packages {pagestep}

Install the new dependencies:

```bash
# If using requirements_32bit.txt (for 32-bit Raspberry Pi OS)
pip install -r software/requirements_32bit.txt

# OR install specific new packages manually
pip install PyYAML>=6.0
pip install "numpy>=1.19.0,<2.0.0"
pip install "opencv-python-headless>=4.5.0,<5.0.0"  # Use headless version (faster installation on Pi)
pip install python-socketio>=5.0.0

# Upgrade existing packages (optional, will happen automatically with requirements.txt)
pip install --upgrade Flask Flask-SocketIO Werkzeug Jinja2 MarkupSafe itsdangerous
```

**Note:** If you encounter conflicts, you may need to upgrade packages individually or use `pip install --upgrade` for specific packages.

### Step 5: Configure Strobe Control Mode {pagestep}

The new code supports both strobe-centric and camera-centric control modes. You need to select the mode that matches your firmware.

**Important:** You need to know which firmware you have installed:
- **Old firmware** (software trigger) → Use `strobe-centric` mode
- **New firmware** (hardware trigger) → Use `camera-centric` mode

You can perfectly fine keep working with your 32-bit-only version if it's already working for you. The strobe-centric mode is only on 32-bit because it requires the picamera package (32-bit only), but it works perfectly well.

#### Option A: Using Environment Variable (Recommended)

**For desktop launcher or startup script:**

If you use a desktop launcher (`.desktop` file), edit it to include the environment variable:

```ini
[Desktop Entry]
Exec=env RIO_STROBE_CONTROL_MODE=strobe-centric python /home/pi/open-microfluidics-workstation/software/main.py
```

**For `/etc/rc.local` startup:**

```bash
sudo nano /etc/rc.local
```

Add before the application line:

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric
sudo -H -u pi python3 /home/pi/open-microfluidics-workstation/software/main.py &
```

**For command line:**

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric
python /home/pi/open-microfluidics-workstation/software/main.py
```

#### Option B: Edit config.py Directly

Edit `software/config.py` and change:

```python
STROBE_CONTROL_MODE = os.getenv("RIO_STROBE_CONTROL_MODE", "strobe-centric").lower()
```

This sets strobe-centric mode as the default.

**Mode Selection:**
- **`strobe-centric`**: Strobe timing controls camera exposure (software trigger). **Use this if you have firmware that supports software trigger mode.** Works on 32-bit only (due to picamera package requirement).
- **`camera-centric`**: Camera frame callback triggers strobe via GPIO (hardware trigger). **Use this if you have new firmware with hardware trigger support.** Provides better synchronization.

### Step 6: Update Startup Script {pagestep}

If you're running the app on startup, update `/etc/rc.local`:

```bash
sudo nano /etc/rc.local
```

Update the line to:

```bash
export RIO_STROBE_CONTROL_MODE=strobe-centric
sudo -H -u pi python3 /home/pi/open-microfluidics-workstation/software/main.py &
```

**Important:** Make sure to set `RIO_STROBE_CONTROL_MODE` before running the application. Use `strobe-centric` for old firmware, or `camera-centric` for new firmware.

### Step 7: Test the Installation {pagestep}

1. **Stop any running instance:**

```bash
# Find and kill existing process
ps aux | grep python | grep main.py
sudo kill -9 <PID>  # Replace <PID> with the process ID
```

2. **Start the application:**

```bash
# With environment variable set (use strobe-centric for old firmware)
export RIO_STROBE_CONTROL_MODE=strobe-centric
cd /home/pi/open-microfluidics-workstation/software
python main.py
```

Or if you edited `config.py` directly:

```bash
cd /home/pi/open-microfluidics-workstation/software
python main.py
```

3. **Check the logs** - You should see:

**For strobe-centric mode:**
```
INFO - Strobe control mode: strobe-centric (hardware_trigger=False)
INFO - Strobe configured for software trigger mode
```

**For camera-centric mode:**
```
INFO - Strobe control mode: camera-centric (hardware_trigger=True)
INFO - Strobe configured for hardware trigger mode
```

4. **Access the web interface:**

Open your browser and go to `https://0.0.0.0:5000` (or your Pi's IP address).

---

## Configuration Modes Explained

### Strobe-Centric Mode

- **Trigger Mode:** Software trigger (trigger_mode = 0)
- **Control:** Strobe timing controls camera exposure
- **Frame Callback:** Not used
- **Firmware:** Compatible with firmware that supports software trigger mode
- **Platform:** 32-bit Raspberry Pi OS only (requires picamera package, which is 32-bit only)
- **Use Case:** Existing working 32-bit systems. This mode works perfectly fine if you already have a working system.
- **Note:** Replaced by camera-centric mode with new strobe chip firmware for better synchronization, but this mode is fully functional.

### Camera-Centric Mode

- **Trigger Mode:** Hardware trigger (trigger_mode = 1)
- **Control:** Camera frame callback triggers strobe via GPIO
- **Frame Callback:** Used to trigger PIC via GPIO pin 18 (BCM numbering)
- **Firmware:** Requires new firmware with hardware trigger support
- **Platform:** 32-bit or 64-bit (uses picamera2 on 64-bit, or picamera on 32-bit)
- **Use Case:** New hardware/firmware deployment or when better synchronization is needed

---

## Troubleshooting

### Issue: Package Installation Fails

**Problem:** `pip install` fails with dependency conflicts.

**Solution:**

```bash
# Try upgrading pip first
pip install --upgrade pip

# Install packages individually if batch install fails
pip install PyYAML --upgrade
pip install numpy --upgrade
# etc.
```

### Issue: Application Won't Start

**Problem:** Errors during startup.

**Solution:**

1. Check that you're using the correct Python environment:
   ```bash
   which python
   python --version
   ```

2. Verify all packages are installed:
   ```bash
   pip list | grep -E "Flask|PyYAML|numpy|opencv|socketio"
   ```

3. Check logs for specific error messages:
   ```bash
   python main.py 2>&1 | tee startup.log
   ```

### Issue: Strobe Not Working

**Problem:** Strobe doesn't respond or works incorrectly.

**Solution:**

1. Verify control mode is set correctly:
   ```bash
   echo $RIO_STROBE_CONTROL_MODE  # Should output "strobe-centric" or "camera-centric"
   ```

2. Check application logs for mode confirmation:
   ```
   INFO - Strobe control mode: strobe-centric
   ```
   or
   ```
   INFO - Strobe control mode: camera-centric
   ```

3. Ensure firmware is compatible with selected mode:
   - **Strobe-centric mode** requires firmware with software trigger support
   - **Camera-centric mode** requires new firmware with hardware trigger support

4. Verify you're using the correct mode for your firmware version

### Issue: Camera Not Working

**Problem:** Camera initialization fails.

**Solution:**

1. Verify camera is enabled:
   ```bash
   vcgencmd get_camera
   # Should show: supported=1 detected=1
   ```

2. Check camera module is loaded:
   ```bash
   lsmod | grep bcm2835
   ```

3. Test camera directly:
   ```bash
   raspistill -o test.jpg
   ```

### Issue: GPIO Permission Errors

**Problem:** Permission denied when accessing GPIO.

**Solution:**

```bash
# Add user to gpio group (if not already added)
sudo usermod -a -G gpio pi

# Or run with sudo (not recommended for production)
sudo python main.py
```

---

## Rollback Procedure

If you need to revert to the old installation:

```bash
# Stop the application
sudo pkill -f "python.*main.py"

# Restore backup
sudo cp -r /home/pi/webapp_backup /home/pi/webapp

# Switch back to master branch
cd /home/pi/open-microfluidics-workstation
git checkout master
git pull origin master

# Restart old application
sudo -H -u pi python3 /home/pi/webapp/pi_webapp.py &
```

---

## Summary of Changes

1. **New packages:** PyYAML, numpy, opencv-python-headless (recommended) or opencv-python, python-socketio
2. **Updated packages:** Flask, Flask-SocketIO, Werkzeug, Jinja2, MarkupSafe, itsdangerous
3. **Configuration:** New environment variable `RIO_STROBE_CONTROL_MODE`:
   - Use `"strobe-centric"` for firmware with software trigger support (32-bit only)
   - Use `"camera-centric"` for new firmware with hardware trigger support
4. **Code location:** Changed from `/home/pi/webapp/` to `/home/pi/open-microfluidics-workstation/software/`
5. **Main file:** Changed from `pi_webapp.py` to `main.py`

---

## Next Steps

After successful installation and testing:

1. Test all functionality with your current firmware mode (strobe-centric or camera-centric)
2. If you have a working 32-bit system with strobe-centric mode, you can continue using it - it works perfectly fine
3. When ready (and if you want better synchronization), you can:
   - Update firmware to support hardware trigger mode
   - Switch to camera-centric mode: `export RIO_STROBE_CONTROL_MODE=camera-centric`
   - Test hardware trigger functionality

---

## Configuration File Examples

Example configuration files are available in the `software/configurations/` directory:

1. **Strobe Only 32-bit (with droplet detection)**: `config-example-strobe-only-32bit.yaml`
   - For Raspberry Pi with strobe module and camera
   - Uses strobe-centric mode (software trigger)
   - 32-bit only (requires picamera package)
   - Works perfectly fine if you already have a working 32-bit system
   - **Legacy detailed example**: `config-example-strobe-centric-32bit.yaml`

2. **Strobe Only 64-bit (with droplet detection)**: `config-example-strobe-only-64bit.yaml`
   - For Raspberry Pi with strobe module and camera
   - Uses camera-centric mode (hardware trigger)
   - Requires new firmware with hardware trigger support

3. **Full Features 64-bit (with droplet detection)**: `config-example-full-features-64bit.yaml`
   - For complete system with strobe, camera, flow controller, and heaters
   - Uses camera-centric mode (hardware trigger)
   - Requires new firmware with hardware trigger support
   - **Legacy detailed example**: `config-example-camera-centric-64bit.yaml`

**Note:** 
- Configuration is done via environment variables (e.g., `RIO_STROBE_CONTROL_MODE`)
- Camera resolution and snapshot settings can be adjusted via the web interface (Camera Configuration tab)
- YAML files show default values and serve as documentation; UI settings override config file defaults
- Framerate is automatically optimized from strobe timing (use "Optimize" button in UI)

## Additional Resources

- [Advanced Installation Guide](https://github.com/wenzel-lab/strobe-enhanced-microscopy-stage/blob/main/software/advanced-installation.md) (original installation instructions)
- [Configuration Quick Reference](../software/configurations/configuration-quick-reference.md) - Complete configuration guide
- Repository: https://github.com/wenzel-lab/open-microfluidics-workstation
- Branch: `strobe-rewrite`
- Example Configurations (in `software/configurations/`):
  - `config-example-strobe-only-32bit.yaml` (recommended)
  - `config-example-strobe-only-64bit.yaml` (recommended)
  - `config-example-full-features-64bit.yaml` (recommended)
  - `config-example-strobe-centric-32bit.yaml` (detailed reference)
  - `config-example-camera-centric-64bit.yaml` (detailed reference)

---

## Questions or Issues?

If you encounter problems not covered in this guide:

1. Check application logs for error messages
2. Verify all prerequisites are met
3. Ensure firmware compatibility with selected mode
4. Review repository issues or documentation
5. Check example configuration files for your platform type


