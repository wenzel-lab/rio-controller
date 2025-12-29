# Socket.IO Upgrade Test - Simple Instructions

## Overview

Test upgraded Socket.IO versions (Flask-SocketIO 5.x) without affecting your production setup.

## Files Included in Deployment

When you rsync `pi-deployment/`, these files are included:
- ✅ `requirements-webapp-only-32bit-upgraded.txt` - Upgraded packages
- ✅ `SOCKETIO_UPGRADE_PI.sh` - Automated test script
- ✅ `SOCKETIO_UPGRADE_README.md` - Quick reference

## Workflow

### 1. Copy Files to pi-deployment (One Time)

```bash
cd /Users/twenzel/Documents/GitHub/rio-controller

# Copy the upgraded requirements file
cp software/requirements-webapp-only-32bit-upgraded.txt pi-deployment/

# Copy the test script
cp SOCKETIO_UPGRADE_PI.sh pi-deployment/
chmod +x pi-deployment/SOCKETIO_UPGRADE_PI.sh
```

### 2. Deploy to Pi

```bash
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

### 3. Test on Pi

```bash
ssh pi@raspberrypi.local
cd ~/rio-controller
./SOCKETIO_UPGRADE_PI.sh
```

## What Gets Tested

- Flask-SocketIO 5.4.x (upgrade from 4.3.2)
- python-socketio 5.11.x (upgrade from 4.7.1)
- python-engineio 4.9.x (upgrade from 3.13.2)

## Production vs Test

- **Production**: `requirements-webapp-only-32bit.txt` (Flask-SocketIO 4.3.2)
- **Test**: `requirements-webapp-only-32bit-upgraded.txt` (Flask-SocketIO 5.4+)

Both files are available on the Pi. The test uses a virtual environment so it doesn't affect production.

## After Testing

If the upgrade works well:
- You can update production requirements to use the upgraded versions
- Or continue using the upgraded file for future deployments

If there are issues:
- Just deactivate the test environment
- Production continues using the original versions

