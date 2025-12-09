# Import Path Fix for Webapp Controllers

## Issue

**Error**: `ImportError: cannot import name 'CameraController' from 'controllers' (unknown location)`

**Root Cause**: Naming conflict between two `controllers` directories:
- `software/controllers/` - Device controllers (flow_web, heater_web, camera, strobe_cam)
- `software/rio-webapp/controllers/` - Web controllers (camera_controller, flow_controller, etc.)

When Python tried to import `from controllers import ...`, it couldn't determine which `controllers` package to use.

## Solution

Changed `main.py` to import directly from the controller files in `rio-webapp/controllers/` rather than trying to import from a package:

### Before (Broken):
```python
rio_webapp_dir = os.path.join(software_dir, 'rio-webapp')
sys.path.insert(0, rio_webapp_dir)
from controllers import CameraController, ...  # Ambiguous - which controllers?
```

### After (Fixed):
```python
rio_webapp_controllers_dir = os.path.join(software_dir, 'rio-webapp', 'controllers')
sys.path.insert(0, rio_webapp_controllers_dir)
# Import directly from files to avoid package name conflict
from camera_controller import CameraController
from flow_controller import FlowController
from heater_controller import HeaterController
from view_model import ViewModel
```

## Additional Fixes

Also updated relative imports in controller files:
- `flow_controller.py`: Changed `from .view_model import ViewModel` to `from view_model import ViewModel`
- `heater_controller.py`: Changed `from .view_model import ViewModel` to `from view_model import ViewModel`
- All controller files: Added path checks before inserting into `sys.path` to avoid duplicates

## Verification

The import path structure is now correct. Any `ModuleNotFoundError` for `flask_socketio` or other packages is just a missing dependency issue - install with:

```bash
mamba activate rio-controller
pip install -r requirements-simulation.txt  # For Mac/PC
# OR
pip install -r requirements_32bit.txt  # For 32-bit Pi
# OR
pip install -r requirements_64bit.txt  # For 64-bit Pi
```

