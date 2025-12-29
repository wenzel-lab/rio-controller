# Socket.IO Upgrade Test - Quick Reference

## On Raspberry Pi

```bash
# IMPORTANT: Navigate to the rio-controller directory first!
cd ~/rio-controller

# Create test environment
python3 -m venv venv-socketio-test
source venv-socketio-test/bin/activate
pip install --upgrade pip
pip install -r pi-deployment/requirements-webapp-only-32bit-upgraded.txt

# Check versions
python3 -c "import flask_socketio, socketio, engineio; print(f'Flask-SocketIO: {flask_socketio.__version__}, python-socketio: {socketio.__version__}, python-engineio: {engineio.__version__}')"

# Test the application
python pi-deployment/main.py
```

## Verify Installation

After installation, you should see:
- Flask-SocketIO: 5.4.x or higher
- python-socketio: 5.11.x or higher  
- python-engineio: 4.9.x or higher

## Test Checklist

- [ ] Application starts without errors
- [ ] WebSocket connection establishes
- [ ] Camera feed updates work
- [ ] ROI selection works
- [ ] Strobe controls work
- [ ] All buttons respond correctly
- [ ] No console errors in browser
- [ ] No errors in server logs

## Rollback if Needed

```bash
deactivate
source venv-rio/bin/activate  # Your original environment
```

