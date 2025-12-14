# Fixing opencv-python Installation on Raspberry Pi

## Problem

opencv-python can take hours to build from source on Raspberry Pi. It's better to use pre-built wheels or opencv-python-headless.

## Solution

### Option 1: Use opencv-python-headless (Recommended)

This is a lighter version without GUI dependencies, perfect for headless Pi:

```bash
cd ~/rio-controller
source venv-rio/bin/activate  # If venv is in rio-controller
# OR if venv is in home:
source ~/venv-rio/bin/activate

# Uninstall any partial opencv installation
pip uninstall opencv-python opencv-python-headless -y

# Install headless version (faster, pre-built wheels available)
pip install "opencv-python-headless>=4.5.0,<5.0.0"
```

### Option 2: Ensure venv is in the right location

You created venv in `~/venv-rio` but code is in `~/rio-controller`. You have two choices:

**Option A: Use venv from home directory**
```bash
cd ~/rio-controller
source ~/venv-rio/bin/activate
```

**Option B: Create venv in rio-controller (Recommended)**
```bash
cd ~/rio-controller
rm -rf venv-rio  # Remove if exists
python3 -m venv venv-rio
source venv-rio/bin/activate
```

Then install packages again.

### Option 3: Force pre-built wheel (if available for your Pi)

For 64-bit Pi, you can try forcing wheel installation:

```bash
pip install --only-binary :all: "opencv-python>=4.5.0,<5.0.0"
```

If that fails (no wheel available), fall back to headless version.

## Complete Correct Setup

```bash
# 1. Go to deployment directory
cd ~/rio-controller

# 2. Create venv in the right place (if you haven't already)
python3 -m venv venv-rio

# 3. Activate it
source venv-rio/bin/activate

# 4. Upgrade pip
pip install --upgrade pip

# 5. Install packages (using headless opencv)
pip install "Flask>=2.0.0,<4.0.0"
pip install "Flask-SocketIO>=5.0.0,<6.0.0"
pip install "Werkzeug>=2.0.0,<4.0.0"
pip install "Jinja2>=3.0.0"
pip install "MarkupSafe>=2.0.0"
pip install "itsdangerous>=2.0.0"
pip install "python-socketio>=5.0.0"
pip install "opencv-python-headless>=4.5.0,<5.0.0"  # Use headless version
pip install "PyYAML>=6.0"
```

## Or Use the Setup Script

The setup script should handle this, but if opencv is the issue, you can modify it or run manually with headless version.
