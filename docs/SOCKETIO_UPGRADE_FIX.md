# Socket.IO Upgrade - Eventlet Fix

## Problem

After installing upgraded packages, running the application fails with:

```
AttributeError: module 'distutils' has no attribute 'version'
```

This happens because:
1. Eventlet is installed system-wide (in `~/.local/lib/python3.9/site-packages/`)
2. With `--system-site-packages`, pip sees the system eventlet first
3. When you run `pip install eventlet`, it says "already satisfied" and doesn't install in venv
4. The system eventlet tries to use `distutils.version` which causes issues

## Solution

Force install eventlet in the venv using `--force-reinstall --no-deps`:

```bash
pip install --force-reinstall --no-deps "eventlet>=0.33.0,<1.0.0"
pip install "dnspython>=1.15.0" "greenlet>=0.3" "six>=1.10.0"
```

The updated script (`SOCKETIO_UPGRADE_PI.sh`) now does this automatically.

## Quick Fix on Pi

If you already ran the script and got the error:

```bash
cd ~/rio-controller
source venv-socketio-test/bin/activate

# Force install eventlet in venv (overrides system version)
pip install --force-reinstall --no-deps "eventlet>=0.33.0,<1.0.0"
pip install "dnspython>=1.15.0" "greenlet>=0.3" "six>=1.10.0"

# Verify it's using venv version
python -c "import eventlet; print('Eventlet location:', eventlet.__file__)"
# Should show: /home/pi/rio-controller/venv-socketio-test/...

# Now try running the app
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

## Or Re-run Script

The updated script will handle this automatically:

```bash
# Delete old venv
rm -rf venv-socketio-test

# Re-run script (now force-installs eventlet in venv)
./SOCKETIO_UPGRADE_PI.sh
```

## Why This Works

- `--force-reinstall`: Forces pip to reinstall even if it thinks it's satisfied
- `--no-deps`: Installs eventlet first, then we install dependencies separately
- This ensures eventlet is in the venv, not just found from system
- The venv eventlet is compatible with Flask-SocketIO 5.x
- Still has access to system hardware packages via `--system-site-packages`

## Testing

This fix was tested on Mac in a test virtual environment to ensure:
- Eventlet can be force-installed in a venv with `--system-site-packages`
- Flask-SocketIO 5.x works correctly
- No packages are installed to base Python
