# Socket.IO Upgrade Test - Quick Start

## On Raspberry Pi

After rsync, you'll have these files in `~/rio-controller/`:
- `requirements-webapp-only-32bit-upgraded.txt` - Upgraded Socket.IO packages
- `SOCKETIO_UPGRADE_PI.sh` - Automated test script

## Quick Test

```bash
cd ~/rio-controller
./SOCKETIO_UPGRADE_PI.sh
```

This will:
1. Create a test virtual environment
2. Install upgraded Socket.IO packages
3. Show installed versions

## Manual Test

```bash
cd ~/rio-controller
# Create venv with system site packages (to access hardware libraries)
python3 -m venv --system-site-packages venv-socketio-test
source venv-socketio-test/bin/activate
pip install --upgrade pip
pip install -r requirements-webapp-only-32bit-upgraded.txt

# Verify versions
python3 -c "import flask_socketio, socketio, engineio; print(f'Flask-SocketIO: {flask_socketio.__version__}'); print(f'python-socketio: {socketio.__version__}'); print(f'python-engineio: {engineio.__version__}')"

# Test the application
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
```

## Expected Versions

- Flask-SocketIO: 5.4.x or higher
- python-socketio: 5.11.x or higher
- python-engineio: 4.9.x or higher

## Rollback

```bash
deactivate
# Use your original environment
```
