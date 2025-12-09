# Repository Reorganization Plan

## Proposed Structure

```
open-microfluidics-workstation/
├── software/
│   ├── rio-webapp/              # Main Flask web application
│   │   ├── app.py              # Main entry point (renamed from pi_webapp_refactored.py)
│   │   ├── config.py           # Configuration
│   │   ├── controllers/        # MVC controllers
│   │   ├── templates/          # HTML templates
│   │   └── static/             # JavaScript, CSS
│   ├── drivers/                # Low-level device drivers
│   │   ├── camera/             # Camera abstraction layer
│   │   ├── spi_handler.py      # SPI communication
│   │   └── gpio_handler.py     # GPIO communication
│   ├── controllers/            # Device controllers (flow, heater, strobe, camera)
│   │   ├── flow.py
│   │   ├── heater.py
│   │   ├── strobe.py
│   │   └── camera.py
│   ├── simulation/              # Simulation layer
│   └── droplet-detection/      # Droplet detection algorithms (future)
├── firmware/
│   ├── strobe-pic/              # Strobe PIC firmware
│   ├── pressure-flow-pic/       # Pressure/flow PIC firmware
│   └── heater-pic/              # Heater PIC firmware
├── hardware-modules/
│   ├── strobe-imaging/          # PCB, 3D files, BOM
│   ├── pressure-flow-control/   # PCB, 3D files, BOM
│   ├── heating-stirring/        # PCB, 3D files, BOM
│   └── rpi-hat/                 # Raspberry Pi HAT board
├── docs/                        # Documentation
├── README.md
└── LICENSE.md
```

## Rationale

### Why This Structure?

1. **Clear Separation of Concerns:**
   - `software/` - All software code
   - `firmware/` - All microcontroller firmware
   - `hardware-modules/` - Physical hardware designs (PCB, 3D, BOM)

2. **Eliminates "src" Intermediate Folder:**
   - Direct access: `software/rio-webapp/app.py` instead of `user-interface-software/src/webapp/pi_webapp_refactored.py`
   - Clearer hierarchy

3. **Logical Grouping:**
   - `rio-webapp/` - Complete web application (MVC structure)
   - `drivers/` - Low-level hardware abstraction
   - `controllers/` - High-level device control logic
   - `simulation/` - Testing without hardware

4. **Scalability:**
   - Easy to add new modules (e.g., `droplet-detection/`)
   - Clear where new code belongs

## File Consolidation

### Files to Remove:
- `pi_webapp.py` (old version) → replaced by `pi_webapp_refactored.py`
- `index.html` (old version) → replaced by `index_modern.html`
- `roi_selector_refactored.js` → consolidate into `roi_selector.js` if needed

### Files to Rename:
- `pi_webapp_refactored.py` → `app.py`
- `index_modern.html` → `index.html`
- Keep `roi_selector.js` (currently used)

## Migration Steps

1. Create new folder structure
2. Move files to new locations
3. Update all import paths
4. Update documentation references
5. Test that everything works
6. Remove old files and folders

