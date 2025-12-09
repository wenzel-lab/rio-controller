# Structure Rationale: main.py and config.py Location

## Decision: Both files at `software/` level

Both `main.py` and `config.py` are located at the `software/` folder level (not in `rio-webapp/`).

## Reasoning

### main.py at software/ level

**Why:**
1. **System Orchestrator**: `main.py` is the entry point that imports and coordinates modules from across the entire software structure:
   - `drivers/` (SPI, GPIO, camera abstraction)
   - `controllers/` (device controllers)
   - `simulation/` (simulation layer)
   - `rio-webapp/controllers/` (web layer controllers)

2. **Top-Level Entry Point**: It's the main entry point for the entire software system, not just the webapp. If other entry points were added (CLI, API server, etc.), they would also be at this level.

3. **Logical Hierarchy**: The orchestrator belongs at the same level as the modules it orchestrates.

4. **Standard Python Practice**: Common pattern in Python projects where the main script is at the project root.

### config.py at software/ level

**Why:**
1. **System-Wide Configuration**: `config.py` contains configuration for the entire system:
   - Camera settings (used by `controllers/camera.py`)
   - Strobe settings (used by `controllers/strobe_cam.py`)
   - Flow settings (used by `controllers/flow_web.py`)
   - SPI settings (used by `drivers/`)
   - Heater settings

2. **Shared Across Modules**: Multiple modules across different folders import from `config.py`:
   - `controllers/camera.py`
   - `controllers/strobe_cam.py`
   - `controllers/flow_web.py`
   - Potentially future modules

3. **Not Webapp-Specific**: The configuration is hardware/system configuration, not webapp-specific (like Flask routes, template settings, etc.).

4. **Easier Imports**: When at `software/` level, all modules can import it with a simple path setup, rather than needing to navigate to `rio-webapp/`.

## Structure

```
software/
├── main.py              # System entry point (orchestrates all modules)
├── config.py            # System-wide configuration
├── rio-webapp/          # Web application components
│   ├── controllers/    # Web layer controllers
│   ├── templates/      # HTML templates
│   └── static/         # JavaScript, CSS
├── drivers/            # Hardware drivers
├── controllers/        # Device controllers
└── simulation/         # Simulation layer
```

## Alternative Considered

**Keeping in `rio-webapp/`:**
- Would make sense if `main.py` was ONLY a webapp entry point
- Would make sense if `config.py` was ONLY webapp configuration
- But both are system-wide, so they belong at the system level

## Conclusion

Placing both files at `software/` level provides:
- Clearer architecture (system entry point at system level)
- Easier imports (all modules can access config)
- Better scalability (other entry points can be added at same level)
- Logical organization (orchestrator with the modules it orchestrates)

