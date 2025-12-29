# Socket.IO Upgrade Test - Troubleshooting

## Problem: ModuleNotFoundError for Hardware Libraries

### Symptom

```
ModuleNotFoundError: No module named 'spidev'
Hardware libraries not available (No module named 'spidev')
```

### Cause

Virtual environments isolate Python packages. When you create a venv without `--system-site-packages`, it cannot access system-wide packages like:
- `spidev` (SPI communication)
- `RPi.GPIO` (GPIO control)
- `picamera` (camera interface)
- `numpy`, `Pillow`, `eventlet` (if installed system-wide)

### Solution

Create the virtual environment with `--system-site-packages`:

```bash
# Delete old venv if it exists
rm -rf venv-socketio-test

# Create new venv with system site packages
python3 -m venv --system-site-packages venv-socketio-test
source venv-socketio-test/bin/activate
pip install --upgrade pip
pip install -r requirements-webapp-only-32bit-upgraded.txt
```

### How It Works

- `--system-site-packages`: Allows the venv to access packages installed in system Python
- Hardware packages (spidev, RPi.GPIO, picamera) remain in system Python
- Socket.IO packages are installed in the venv (isolated for testing)
- Best of both worlds: system hardware access + isolated Socket.IO testing

### Alternative: Install Hardware Packages in Venv

If you prefer not to use `--system-site-packages`, you can install hardware packages in the venv:

```bash
pip install spidev RPi.GPIO picamera numpy Pillow eventlet
```

However, this is not recommended because:
- Hardware packages are typically installed system-wide on Pi
- May cause version conflicts
- More complex to manage

## Problem: Eventlet Deprecation Warning

### Symptom

```
DeprecationWarning: Eventlet is deprecated...
```

### Explanation

This is just a warning, not an error. Eventlet is being maintained in bugfix mode but is deprecated for new projects. Flask-SocketIO 5.x still supports Eventlet, so this warning can be ignored for now.

### Future Consideration

Flask-SocketIO 5.x supports multiple async frameworks:
- Eventlet (current, deprecated but functional)
- Gevent (alternative)
- Threading (fallback)

You can switch to Gevent in the future if needed, but Eventlet works fine for testing.

## Problem: Application Still Uses Old Socket.IO

### Symptom

After installing upgraded packages, the application still uses old versions.

### Solution

1. **Check which Python is being used:**
   ```bash
   which python
   python --version
   ```

2. **Make sure venv is activated:**
   ```bash
   source venv-socketio-test/bin/activate
   # You should see (venv-socketio-test) in your prompt
   ```

3. **Verify installed versions:**
   ```bash
   pip list | grep -i socket
   ```

4. **Check if packages are installed:**
   ```bash
   python -c "import flask_socketio; print(flask_socketio.__version__)"
   ```

## Problem: Port Already in Use

### Symptom

```
OSError: [Errno 98] Address already in use
```

### Solution

1. **Find and stop the running process:**
   ```bash
   pkill -f "python.*main.py"
   # Or find the PID:
   ps aux | grep "python.*main.py"
   kill <PID>
   ```

2. **Or use a different port:**
   ```bash
   export RIO_PORT=5001
   python main.py
   ```

## Problem: Import Errors After Upgrade

### Symptom

Various import errors or missing modules after upgrading.

### Solution

1. **Reinstall all packages:**
   ```bash
   pip install --upgrade --force-reinstall -r requirements-webapp-only-32bit-upgraded.txt
   ```

2. **Check for conflicting installations:**
   ```bash
   pip list | grep -i socket
   pip list | grep -i flask
   ```

3. **Clean and reinstall:**
   ```bash
   pip uninstall Flask-SocketIO python-socketio python-engineio -y
   pip install -r requirements-webapp-only-32bit-upgraded.txt
   ```

## Quick Fix Script

If you're having issues, try this complete reset:

```bash
cd ~/rio-controller

# Remove old venv
rm -rf venv-socketio-test

# Create new venv with system packages
python3 -m venv --system-site-packages venv-socketio-test
source venv-socketio-test/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install upgraded packages
pip install -r requirements-webapp-only-32bit-upgraded.txt

# Verify
python -c "import flask_socketio, socketio, engineio; print(f'Flask-SocketIO: {flask_socketio.__version__}'); print(f'python-socketio: {socketio.__version__}'); print(f'python-engineio: {engineio.__version__}')"
```

