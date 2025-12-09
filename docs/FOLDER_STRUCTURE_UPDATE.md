# Folder Structure Update Summary

## Current Structure (Updated)

The software has been reorganized from the old structure to a cleaner, more maintainable structure:

### New Structure

```
open-microfluidics-workstation/
├── software/                    # Main software directory
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration constants
│   ├── rio-webapp/             # Web application components
│   │   ├── controllers/        # MVC controllers (web layer)
│   │   ├── templates/          # HTML templates
│   │   └── static/             # JavaScript, CSS
│   ├── drivers/                # Low-level device drivers
│   │   ├── spi_handler.py
│   │   ├── flow.py
│   │   ├── heater.py
│   │   ├── strobe.py
│   │   └── camera/             # Camera abstraction layer
│   ├── controllers/            # High-level device controllers
│   │   ├── flow_web.py
│   │   ├── heater_web.py
│   │   ├── camera.py
│   │   └── strobe_cam.py
│   ├── simulation/              # Simulation layer
│   └── droplet-detection/      # Droplet detection (future)
│
├── firmware/                    # PIC microcontroller firmware
├── hardware-modules/            # Hardware module designs
└── docs/                        # Documentation
```

### Old Structure (Deprecated)

```
open-microfluidics-workstation/
├── user-interface-software/    # OLD - Legacy software
│   └── src/
│       ├── webapp/             # OLD webapp location
│       ├── simulation/         # OLD simulation location
│       └── droplet_detection/  # OLD droplet detection location
```

## Key Changes

1. **Eliminated `src/` folder**: Direct access to modules
2. **Consolidated to `software/`**: All software in one top-level directory
3. **Separated concerns**: `drivers/`, `controllers/`, `rio-webapp/` clearly separated
4. **Moved entry point**: `main.py` at `software/` level (not in subfolder)

## Updated Documentation

The following documentation has been updated to reflect the new structure:
- `software/README.md` - Main software documentation
- `README.md` - Main repository README (references new location)
- `user-interface-software/README.md` - Notes that it's legacy
- `software/ENVIRONMENT_SETUP.md` - Updated paths
- `software/ENVIRONMENT_ACTIVATION.md` - Updated structure info

## Migration Notes

If you're migrating from the old structure:
1. Use `software/main.py` instead of `user-interface-software/src/webapp/pi_webapp.py`
2. Import paths have changed - see `software/README.md` for details
3. Configuration is now in `software/config.py`
4. Simulation mode still works the same: `RIO_SIMULATION=true python main.py`

## Running the Software

```bash
cd software
mamba activate rio-simulation  # or your environment
RIO_SIMULATION=true python main.py 5001
```

See `software/README.md` for complete instructions.

