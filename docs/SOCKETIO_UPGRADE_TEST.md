# Socket.IO Upgrade Test Guide

## Current Setup
- **Client**: Socket.IO v2.3.0 (CDN)
- **Server**: Flask-SocketIO==4.3.2, python-socketio==4.7.1, python-engineio==3.13.2

## Proposed Upgrade
- **Client**: Keep v2.3.0 (backward compatible) OR upgrade to v4.7.2
- **Server**: Flask-SocketIO>=5.4.0, python-socketio>=5.11.0, python-engineio>=4.9.0

## Compatibility Notes

Flask-SocketIO 5.x uses:
- python-socketio 5.x (requires python-engineio 4.x)
- Backward compatible with Socket.IO client v2.x, v3.x, and v4.x
- The server automatically handles protocol negotiation

## Testing Steps

### 1. Create Test Environment

**On Raspberry Pi:**

```bash
# IMPORTANT: Navigate to the rio-controller directory first!
# Check your current directory:
pwd

# If you're not in ~/rio-controller, navigate there:
cd ~/rio-controller

# Verify the file exists:
ls -la pi-deployment/requirements-webapp-only-32bit-upgraded.txt

# Create a new virtual environment for testing
python3 -m venv venv-socketio-test
source venv-socketio-test/bin/activate

# Install upgraded versions
pip install --upgrade pip
pip install -r pi-deployment/requirements-webapp-only-32bit-upgraded.txt
```

**Or use the automated test script:**

```bash
cd ~/rio-controller
./test_socketio_upgrade.sh
```

### 2. Test with Current Client (v2.3.0)

The upgraded server should work with the existing client v2.3.0:

1. Start the application:
   ```bash
   python software/main.py
   ```

2. Open the web interface in a browser
3. Test all Socket.IO functionality:
   - Camera feed updates
   - ROI selection
   - Strobe controls
   - Droplet detection (if enabled)
   - Flow/heater controls (if enabled)

4. Check browser console for any errors
5. Check server logs for warnings or errors

### 3. Test with Upgraded Client (v4.7.2) - Optional

If you want to upgrade the client as well:

1. Edit `software/rio-webapp/templates/index.html`:
   ```html
   <!-- OLD -->
   <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.3.0/socket.io.js"></script>
   
   <!-- NEW -->
   <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
   ```

2. Test again with the same steps as above

### 4. Rollback if Needed

If issues occur:

```bash
# Deactivate test environment
deactivate

# Use original requirements
source venv-rio/bin/activate  # Your original environment
pip install -r software/requirements-webapp-only-32bit.txt
```

## Expected Benefits

1. **Performance**: Better WebSocket handling and reduced latency
2. **Security**: Latest security patches
3. **Features**: New Socket.IO features available
4. **Compatibility**: Works with both old and new clients

## Potential Issues to Watch For

1. **Connection Issues**: If clients can't connect, check server logs
2. **Event Handling**: Ensure all `socket.emit()` and `socket.on()` calls work
3. **Reconnection**: Test what happens when connection drops
4. **Performance**: Monitor CPU/memory usage

## Verification Checklist

- [ ] Application starts without errors
- [ ] WebSocket connection establishes successfully
- [ ] Camera feed updates work
- [ ] ROI selection works
- [ ] Strobe controls work
- [ ] All buttons/controls respond correctly
- [ ] No console errors in browser
- [ ] No errors in server logs
- [ ] Reconnection works after network interruption

## Quick Test Command

Run the test script:
```bash
./test_socketio_upgrade.sh
```

This will:
1. Create a test virtual environment
2. Install upgraded packages
3. Show installed versions
4. Provide next steps

## If Upgrade Succeeds

1. Update `requirements-webapp-only-32bit.txt` with new versions:
   ```bash
   cp software/requirements-webapp-only-32bit-upgraded.txt software/requirements-webapp-only-32bit.txt
   cp pi-deployment/requirements-webapp-only-32bit-upgraded.txt pi-deployment/requirements-webapp-only-32bit.txt
   ```

2. Optionally update client to Socket.IO v4.7.2 in `index.html`:
   ```html
   <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
   ```

3. Test on actual Raspberry Pi hardware
4. Commit changes

## If Upgrade Fails

1. Document the specific error
2. Check Flask-SocketIO changelog for breaking changes
3. Consider incremental upgrade (e.g., 4.3.2 → 5.0.0 → 5.4.0)
4. Check if any custom Socket.IO code needs updates

