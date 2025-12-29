# Socket.IO Upgrade - Eventlet Fix

## Problem

After installing upgraded packages, running the application fails with:

```
AttributeError: module 'distutils' has no attribute 'version'
```

This happens because:
1. Eventlet is installed system-wide (in `~/.local/lib/python3.9/site-packages/`)
2. The system eventlet version may have compatibility issues
3. With `--system-site-packages`, the venv sees the system eventlet first
4. The system eventlet tries to use `distutils.version` which can cause issues

## Solution

The requirements file now ensures eventlet is installed in the venv, which overrides the system version.

## Quick Fix on Pi

If you already ran the script and got the error:

```bash
cd ~/rio-controller
source venv-socketio-test/bin/activate

# Install eventlet in the venv (overrides system version)
pip install "eventlet>=0.33.0,<1.0.0"

# Verify it's using venv version
python -c "import eventlet; print(eventlet.__file__)"
# Should show: /home/pi/rio-controller/venv-socketio-test/...

# Now try running the app
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

## Or Re-run Script

The updated script and requirements file will install eventlet in the venv automatically:

```bash
# Delete old venv
rm -rf venv-socketio-test

# Re-run script (now includes eventlet in venv)
./SOCKETIO_UPGRADE_PI.sh
```

## Why This Works

- Installing eventlet in the venv takes precedence over system packages
- The venv eventlet is compatible with Flask-SocketIO 5.x
- Avoids distutils compatibility issues
- Still has access to system hardware packages via `--system-site-packages`

