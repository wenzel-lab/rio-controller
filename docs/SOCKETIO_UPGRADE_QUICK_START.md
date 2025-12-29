# Socket.IO Upgrade - Quick Start Commands

## Step 1: Sync Files to Pi (from Mac/PC)

```bash
cd /Users/twenzel/Documents/GitHub/rio-controller

# Sync all files to Pi
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

## Step 2: SSH into Pi

```bash
ssh pi@raspberrypi.local
```

## Step 3: Navigate to Directory

```bash
cd ~/rio-controller
```

## Step 4: Run Upgrade Script

```bash
./SOCKETIO_UPGRADE_PI.sh
```

This will:
- Create/verify virtual environment with system site packages
- Install upgraded Socket.IO packages (Flask-SocketIO 5.x)
- Force install eventlet in venv to override system version
- Show installed versions

## Step 5: Test the Application

```bash
# Activate the test environment (if not already active)
source venv-socketio-test/bin/activate

# Set environment variables
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true

# Run the application
python main.py
```

## Step 6: Test in Browser

1. Open browser to: `http://raspberrypi.local:5000` (or `http://<PI_IP>:5000`)
2. Test features:
   - Camera feed updates
   - ROI selection (especially vertical slider)
   - Strobe controls (should work now with Socket.IO v4.7.2)
   - Snapshot button
   - All Socket.IO real-time features

## Troubleshooting

### If Script Fails

```bash
# Delete broken venv and try again
rm -rf venv-socketio-test
./SOCKETIO_UPGRADE_PI.sh
```

### If Eventlet Error Occurs

```bash
source venv-socketio-test/bin/activate
pip install "dnspython>=1.15.0" "greenlet>=0.3" "six>=1.10.0"
pip install --force-reinstall --no-deps "eventlet>=0.33.0,<1.0.0"
```

### Check Installed Versions

```bash
source venv-socketio-test/bin/activate
python -c "import flask_socketio, socketio, engineio; print(f'Flask-SocketIO: {flask_socketio.__version__}'); print(f'python-socketio: {socketio.__version__}'); print(f'python-engineio: {engineio.__version__}')"
```

Expected:
- Flask-SocketIO: 5.4.x or higher
- python-socketio: 5.11.x or higher
- python-engineio: 4.9.x or higher

## Rollback

If you need to go back to production version:

```bash
deactivate
# Use system Python or your original venv
python main.py
```

## Files Included in Sync

- `requirements-webapp-only-32bit-upgraded.txt` - Upgraded packages
- `SOCKETIO_UPGRADE_PI.sh` - Automated installation script
- `SOCKETIO_UPGRADE_README.md` - Quick reference
- Updated `index.html` - Socket.IO client v4.7.2 + UI fixes

