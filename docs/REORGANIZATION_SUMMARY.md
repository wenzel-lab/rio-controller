# Repository Reorganization Summary

## New Structure

```
open-microfluidics-workstation/
├── software/
│   ├── rio-webapp/              # Main Flask web application
│   │   ├── app.py              # Main entry point (renamed from pi_webapp_refactored.py)
│   │   ├── config.py
│   │   ├── controllers/        # MVC controllers (web layer)
│   │   ├── templates/          # HTML templates (index_modern.html → index.html)
│   │   └── static/             # JavaScript, CSS
│   ├── drivers/                # Low-level device drivers
│   │   ├── spi_handler.py      # SPI/GPIO (renamed from picommon.py)
│   │   ├── flow.py             # Low-level flow driver (from piflow.py)
│   │   ├── heater.py           # Low-level heater driver (from piholder.py)
│   │   ├── strobe.py           # Low-level strobe driver (from pistrobe.py)
│   │   └── camera/             # Camera abstraction
│   ├── controllers/             # High-level device controllers
│   │   ├── flow_web.py         # Flow web interface
│   │   ├── heater_web.py       # Heater web interface
│   │   ├── camera.py           # Camera controller (from camera_pi.py)
│   │   └── strobe_cam.py       # Strobe-camera integration
│   ├── simulation/              # Simulation layer
│   └── droplet-detection/      # Future droplet detection
├── firmware/
│   ├── strobe-pic/              # Strobe PIC firmware
│   ├── pressure-flow-pic/       # Pressure/flow PIC firmware
│   └── heater-pic/             # Heater PIC firmware
├── hardware-modules/
│   ├── strobe-imaging/          # PCB, 3D files, BOM
│   ├── pressure-flow-control/   # PCB, 3D files, BOM
│   ├── heating-stirring/       # PCB, 3D files, BOM
│   └── rpi-hat/                 # Raspberry Pi HAT
└── docs/                        # Documentation
```

## Key Changes

### Files Consolidated:
- ✅ `pi_webapp.py` (old) → removed
- ✅ `pi_webapp_refactored.py` → `software/rio-webapp/app.py`
- ✅ `index.html` (old) → removed
- ✅ `index_modern.html` → `software/rio-webapp/templates/index.html`
- ✅ `roi_selector_refactored.js` → removed (keeping `roi_selector.js`)

### Files Renamed:
- ✅ `picommon.py` → `drivers/spi_handler.py`
- ✅ `piflow.py` → `drivers/flow.py`
- ✅ `piholder.py` → `drivers/heater.py`
- ✅ `pistrobe.py` → `drivers/strobe.py`
- ✅ `camera_pi.py` → `controllers/camera.py`

### Import Path Updates Needed:

**Old imports:**
```python
import picommon
from piflow import PiFlow
from piholder import PiHolder
from pistrobe import PiStrobe
from camera_pi import Camera
from piflow_web import FlowWeb
from piholder_web import heater_web
```

**New imports:**
```python
from drivers.spi_handler import spi_init, PORT_*, GPIO, spi, etc.
from drivers.flow import PiFlow
from drivers.heater import PiHolder
from drivers.strobe import PiStrobe
from controllers.camera import Camera
from controllers.flow_web import FlowWeb
from controllers.heater_web import heater_web
```

## Rationale

1. **Eliminates "src" folder**: Direct access `software/rio-webapp/app.py` instead of `user-interface-software/src/webapp/pi_webapp_refactored.py`

2. **Clear separation**:
   - `drivers/` - Low-level hardware access (SPI, GPIO, device communication)
   - `controllers/` - High-level device control logic
   - `rio-webapp/` - Complete web application (MVC)

3. **Logical grouping**: Related functionality grouped together

4. **Scalable**: Easy to add new modules (e.g., `droplet-detection/`)

5. **Hardware organization**: Firmware and hardware designs separated from software

## Next Steps

1. ✅ Create new folder structure
2. ✅ Move files to new locations
3. ⚠️ Update all import paths (in progress - many files need updating)
4. ⚠️ Update documentation references
5. ⚠️ Test that everything works
6. ⚠️ Remove old `user-interface-software/` folder

## Files That Need Import Updates

- `software/controllers/flow_web.py`
- `software/controllers/heater_web.py`
- `software/controllers/camera.py`
- `software/controllers/strobe_cam.py`
- `software/drivers/flow.py`
- `software/drivers/heater.py`
- `software/drivers/strobe.py`
- `software/rio-webapp/controllers/*.py`
- `software/simulation/*.py`

