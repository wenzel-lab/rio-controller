# Socket.IO Upgrade Test - Raspberry Pi Instructions

## Overview

This guide explains how to test the Socket.IO upgrade on your Raspberry Pi. The upgrade uses Flask-SocketIO 5.x instead of 4.x, which provides better performance and security.

## Important: Deployment Process

Your deployment process uses `create-pi-deployment.sh` which rebuilds the `pi-deployment` directory. The upgraded requirements file is automatically included when you run the deployment script.

## Step-by-Step Instructions

### Step 1: Update Repository (on Mac/PC)

```bash
cd /Users/twenzel/Documents/GitHub/rio-controller
git pull origin master
```

### Step 2: Create Deployment Package

The deployment script will automatically include the upgraded requirements file:

```bash
./create-pi-deployment.sh
```

This creates `pi-deployment/` with:
- All application code
- `requirements-webapp-only-32bit.txt` (current production version)
- `requirements-webapp-only-32bit-upgraded.txt` (test version)

### Step 3: Deploy to Pi

```bash
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

### Step 4: Test on Pi

SSH into your Pi:

```bash
ssh pi@raspberrypi.local
cd ~/rio-controller
```

**Option A: Use the automated test script**

```bash
./SOCKETIO_UPGRADE_PI.sh
```

**Option B: Manual installation**

```bash
# Create test virtual environment
python3 -m venv venv-socketio-test
source venv-socketio-test/bin/activate

# Install upgraded packages
pip install --upgrade pip
pip install -r requirements-webapp-only-32bit-upgraded.txt

# Verify installation
python3 -c "import flask_socketio, socketio, engineio; print(f'Flask-SocketIO: {flask_socketio.__version__}'); print(f'python-socketio: {socketio.__version__}'); print(f'python-engineio: {engineio.__version__}')"
```

Expected versions:
- Flask-SocketIO: 5.4.x or higher
- python-socketio: 5.11.x or higher
- python-engineio: 4.9.x or higher

### Step 5: Test the Application

```bash
# Make sure virtual environment is activated
source venv-socketio-test/bin/activate

# Set environment variables
export RIO_STROBE_CONTROL_MODE=strobe-centric
export RIO_SIMULATION=false
export RIO_DROPLET_ANALYSIS_ENABLED=true

# Run the application
python main.py
```

### Step 6: Test Functionality

Open the web interface in a browser and test:
- [ ] Camera feed updates
- [ ] ROI selection (especially the vertical slider)
- [ ] Strobe controls
- [ ] Snapshot button
- [ ] All Socket.IO real-time features
- [ ] Check browser console for errors
- [ ] Check server logs for warnings

## Rollback

If the upgrade causes issues:

```bash
# Deactivate test environment
deactivate

# Use your original environment (system Python or venv-rio)
# The production requirements file is still available:
pip install -r requirements-webapp-only-32bit.txt
```

## If Upgrade Succeeds

If testing is successful, you can:

1. **Update production requirements** (optional):
   ```bash
   # On Mac/PC, edit software/requirements-webapp-only-32bit.txt
   # Change Flask-SocketIO and related packages to upgraded versions
   ```

2. **Or keep using the upgraded file**:
   - Rename `requirements-webapp-only-32bit-upgraded.txt` to `requirements-webapp-only-32bit.txt`
   - Update `create-pi-deployment.sh` to use the upgraded version

## Troubleshooting

### File Not Found

If `requirements-webapp-only-32bit-upgraded.txt` is missing:

1. **Check it exists in software directory:**
   ```bash
   # On Mac/PC
   ls -la software/requirements-webapp-only-32bit-upgraded.txt
   ```

2. **Recreate deployment:**
   ```bash
   ./create-pi-deployment.sh
   ```

3. **Verify it's in pi-deployment:**
   ```bash
   ls -la pi-deployment/requirements-webapp-only-32bit-upgraded.txt
   ```

### Installation Errors

If pip install fails:

1. **Check Python version:**
   ```bash
   python3 --version
   ```
   Should be Python 3.7 or higher

2. **Try without cache:**
   ```bash
   pip install --no-cache-dir -r requirements-webapp-only-32bit-upgraded.txt
   ```

3. **Install packages individually:**
   ```bash
   pip install Flask-SocketIO>=5.4.0,<6.0.0
   pip install python-socketio>=5.11.0
   pip install python-engineio>=4.9.0
   ```

### Application Errors

If the application fails to start:

1. **Check for version conflicts:**
   ```bash
   pip list | grep -i socket
   ```

2. **Uninstall conflicting packages:**
   ```bash
   pip uninstall Flask-SocketIO python-socketio python-engineio -y
   pip install -r requirements-webapp-only-32bit-upgraded.txt
   ```

3. **Check server logs** for specific error messages

## Notes

- The upgraded requirements file is automatically included in deployments
- Both requirements files are available on the Pi (production and test)
- The test uses a virtual environment to avoid affecting production
- Flask-SocketIO 5.x is backward compatible with Socket.IO client v2.3.0
- No code changes are required for the upgrade
