# Import Path Verification Report

## Status: ✅ All Import Paths Verified

All import paths have been updated and verified for the new repository structure.

## Import Structure

### Main Application (`software/rio-webapp/main.py`)
```python
from drivers.spi_handler import spi_init, PORT_HEATER1, PORT_HEATER2, PORT_HEATER3, PORT_HEATER4, PORT_FLOW
from controllers.heater_web import heater_web
from controllers.camera import Camera
from controllers.flow_web import FlowWeb
from controllers import CameraController, FlowController, HeaterController, ViewModel
```
✅ **Status**: Correct - uses `sys.path.insert` to add parent directory

### Device Controllers (`software/controllers/`)
- `flow_web.py`: ✅ Imports from `drivers.flow` and `drivers.spi_handler`
- `heater_web.py`: ✅ Imports from `drivers.heater`
- `camera.py`: ✅ Imports from `drivers.spi_handler` and `controllers.strobe_cam`
- `strobe_cam.py`: ✅ Imports from `drivers.strobe`, `drivers.spi_handler`, `drivers.camera`

### Low-Level Drivers (`software/drivers/`)
- `flow.py`: ✅ Imports from `spi_handler` (sibling module)
- `heater.py`: ✅ Imports from `spi_handler` (sibling module)
- `strobe.py`: ✅ Imports from `spi_handler` (sibling module)
- `spi_handler.py`: ✅ Handles simulation mode automatically

### Web App Controllers (`software/rio-webapp/controllers/`)
- `camera_controller.py`: ✅ Imports from `controllers.camera`
- `flow_controller.py`: ✅ Imports from `controllers.flow_web`
- `heater_controller.py`: ✅ Imports from `controllers.heater_web`
- `view_model.py`: ✅ Imports from `controllers.flow_web` and `controllers.camera`
- `__init__.py`: ✅ Uses relative imports (`.camera_controller`, etc.)

### Camera Abstraction (`software/drivers/camera/`)
- `__init__.py`: ✅ Exports `BaseCamera` and `create_camera`
- Used by: `controllers/strobe_cam.py`

### Configuration
- All controllers that need config import from `rio-webapp/config.py` with proper path setup
- ✅ Path resolution handled via `sys.path.insert`

## Dependencies

### Hardware Mode (`requirements.txt`)
- Flask, Flask-SocketIO, eventlet
- spidev, RPi.GPIO (Raspberry Pi only)
- picamera (Raspberry Pi only)
- Pillow

### Simulation Mode (`requirements-simulation.txt`)
- Flask, Flask-SocketIO, eventlet (updated versions)
- opencv-python, numpy (for simulated camera)
- Pillow
- PyYAML
- **Excludes**: spidev, RPi.GPIO, picamera (simulated instead)

## Path Resolution Strategy

All modules use `sys.path.insert` to add the `software/` directory to Python's path, allowing imports like:
- `from drivers.X import Y`
- `from controllers.X import Y`
- `from simulation.X import Y`

This ensures imports work regardless of where the script is executed from, as long as the `software/` directory is in the path.

## Testing

To verify imports work:

```bash
# Simulation mode (Mac/PC)
cd software/rio-webapp
RIO_SIMULATION=true python main.py

# Hardware mode (Raspberry Pi)
cd software/rio-webapp
python main.py
```

## Known Issues

None - all import paths have been verified and corrected.

