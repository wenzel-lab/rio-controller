# Socket.IO Upgrade Test - Raspberry Pi Instructions

## Step 1: Update Your Repository

First, make sure you have the latest files from the repository:

```bash
cd ~/rio-controller
git pull origin master
# OR if you're on a different branch:
# git pull origin <your-branch-name>
```

## Step 2: Verify File Exists

Check that the requirements file is present:

```bash
ls -la pi-deployment/requirements-webapp-only-32bit-upgraded.txt
```

You should see the file listed. If not, the git pull didn't work - check your branch and remote.

## Step 3: Create Test Environment

```bash
# Make sure you're in the rio-controller directory
cd ~/rio-controller
pwd  # Should show: /home/pi/rio-controller

# Create test virtual environment
python3 -m venv venv-socketio-test
source venv-socketio-test/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install upgraded Socket.IO packages
pip install -r pi-deployment/requirements-webapp-only-32bit-upgraded.txt
```

## Step 4: Verify Installation

```bash
python3 -c "import flask_socketio, socketio, engineio; print(f'Flask-SocketIO: {flask_socketio.__version__}'); print(f'python-socketio: {socketio.__version__}'); print(f'python-engineio: {engineio.__version__}')"
```

Expected output:
- Flask-SocketIO: 5.4.x or higher
- python-socketio: 5.11.x or higher
- python-engineio: 4.9.x or higher

## Step 5: Test the Application

```bash
# Make sure virtual environment is activated
source venv-socketio-test/bin/activate

# Run the application
python pi-deployment/main.py
```

## Troubleshooting

### File Not Found Error

If you get `[Errno 2] No such file or directory`:

1. **Check your current directory:**
   ```bash
   pwd
   ```
   Should be: `/home/pi/rio-controller`

2. **If not, navigate there:**
   ```bash
   cd ~/rio-controller
   ```

3. **Check if file exists:**
   ```bash
   ls -la pi-deployment/requirements-webapp-only-32bit-upgraded.txt
   ```

4. **If file doesn't exist, pull latest changes:**
   ```bash
   git pull origin master
   ```

### Installation Errors

If pip install fails:

1. **Check Python version:**
   ```bash
   python3 --version
   ```
   Should be Python 3.7 or higher

2. **Try installing without cache:**
   ```bash
   pip install --no-cache-dir -r pi-deployment/requirements-webapp-only-32bit-upgraded.txt
   ```

3. **Install packages one by one to identify issues:**
   ```bash
   pip install Flask-SocketIO>=5.4.0,<6.0.0
   pip install python-socketio>=5.11.0
   pip install python-engineio>=4.9.0
   ```

## Rollback

If the upgrade causes issues:

```bash
# Deactivate test environment
deactivate

# Use your original environment
source venv-rio/bin/activate  # or whatever your original venv is called
```

