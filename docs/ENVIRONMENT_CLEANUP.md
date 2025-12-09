# Environment Cleanup - System Python Packages Removed

## Issue

Packages were accidentally installed to system Python (`/usr/local/lib/python3.10/site-packages`) instead of the mamba environment.

## Action Taken

All packages have been uninstalled from system Python:
- Flask, Flask-SocketIO, Werkzeug, Jinja2, MarkupSafe, itsdangerous
- eventlet, opencv-python, numpy, Pillow, PyYAML
- python-socketio, python-engineio, and related dependencies

## Next Steps - Install in Mamba Environment

**IMPORTANT**: You must activate your `rio-simulation` environment and install packages there:

```bash
# Activate your mamba environment
mamba activate rio-simulation

# Verify you're in the right environment
which python
# Should show: ~/mambaforge/envs/rio-simulation/bin/python

# Install dependencies in the mamba environment
cd software
pip install -r requirements-simulation.txt

# Verify installation
python -c "import flask_socketio; print('✓ Dependencies installed in mamba environment')"
```

## Verification

After installation, verify packages are in the mamba environment:

```bash
mamba activate rio-simulation
python -c "import flask_socketio; import flask_socketio as fsi; print('Location:', fsi.__file__)"
# Should show: ~/mambaforge/envs/rio-simulation/lib/python3.10/site-packages/...
```

## Prevention

**Never run `pip install` without first activating the mamba environment!**

Always:
1. `mamba activate rio-simulation` (or your target environment)
2. Verify: `which python` shows mamba environment path
3. Then: `pip install -r requirements-simulation.txt`

