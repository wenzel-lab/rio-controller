# Dependency Check Report

## Summary

This report documents all dependencies and potential issues found during dependency scanning.

## External Dependencies

All external packages are listed in `requirements-simulation.txt`:

### Required Packages
- **Flask** (>=2.0.0,<4.0.0) - Web framework
- **Flask-SocketIO** (>=5.0.0,<6.0.0) - WebSocket support
- **Werkzeug** (>=2.0.0,<4.0.0) - WSGI utilities
- **Jinja2** (>=3.0.0) - Template engine
- **MarkupSafe** (>=2.0.0) - String escaping
- **itsdangerous** (>=2.0.0) - Data signing
- **eventlet** (>=0.33.0) - Async networking
- **opencv-python** (>=4.5.0) - Image processing (simulation)
- **numpy** (>=1.19.0) - Numerical computing
- **Pillow** (>=9.0.0) - Image processing
- **PyYAML** (>=6.0) - YAML parsing
- **python-socketio** (>=5.0.0) - Socket.IO client

### Installation

```bash
mamba activate rio-simulation
cd software
pip install -r requirements-simulation.txt
```

## Internal Module Dependencies

### Import Structure

1. **main.py** imports:
   - `drivers.spi_handler` - SPI/GPIO communication
   - `controllers.heater_web` - Heater control
   - `controllers.camera` - Camera control
   - `controllers.flow_web` - Flow control
   - `rio-webapp/controllers/*` - Web controllers

2. **drivers/** modules import:
   - `spi_handler` (relative import)
   - Standard library only (time, os, sys, threading)

3. **controllers/** modules import:
   - `drivers.*` - Hardware drivers
   - `config` - Configuration constants
   - Standard library

4. **rio-webapp/controllers/** import:
   - `controllers.*` - Device controllers
   - `flask_socketio` - WebSocket support
   - Standard library

5. **simulation/** modules import:
   - Standard library only
   - `numpy`, `cv2` (for camera simulation)

## Potential Issues Found

### 1. Missing Dependencies in Environment

**Issue**: If running `test_imports.py` shows missing modules, they need to be installed.

**Solution**: 
```bash
mamba activate rio-simulation
pip install -r requirements-simulation.txt
```

### 2. Import Path Issues

**Status**: ✅ Fixed
- All import paths verified
- `rio-webapp/controllers` imports work correctly
- Relative imports in drivers work correctly

### 3. Config Module

**Status**: ✅ Working
- `config.py` is at `software/` level
- All modules can import it correctly
- Fallback values provided if import fails

### 4. Simulation Mode

**Status**: ✅ Working
- `RIO_SIMULATION=true` environment variable works
- Simulated modules import correctly
- No hardware dependencies when in simulation mode

## Verification Steps

Before running `main.py`, verify:

1. **Environment activated**:
   ```bash
   mamba activate rio-simulation
   which python  # Should show mamba environment path
   ```

2. **Dependencies installed**:
   ```bash
   python test_imports.py
   # Should show all ✓ checks
   ```

3. **Simulation mode set**:
   ```bash
   export RIO_SIMULATION=true
   ```

4. **Run application**:
   ```bash
   python main.py 5001
   ```

## Known Issues

### None Currently

All dependencies are properly declared and import paths are correct.

## Test Script

Use `tests/test_imports.py` to verify all dependencies before running:

```bash
python tests/test_imports.py
```

This will check:
- External package availability
- Internal module imports
- Module initialization
- Configuration loading

