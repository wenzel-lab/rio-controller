## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change behavior or public interfaces, please update this document.

## Purpose

This folder contains **device controllers**: the stateful business logic that orchestrates hardware drivers and exposes higher-level operations to the web layer.

## What belongs here / what does not

- **Belongs here**:
  - coordination logic and state machines for devices (camera+strobe integration, heater state, flow state)
  - mapping between firmware concepts and user-facing concepts (when it is device-specific)
  - performance/robustness guardrails for continuous operation
- **Does not belong here**:
  - direct GPIO/SPI/I2C register-level communication (belongs in `../drivers/`)
  - HTTP routes, template formatting, WebSocket event wiring (belongs in `../rio-webapp/`)
  - UI JavaScript and HTML (belongs in `../rio-webapp/static` and `../rio-webapp/templates`)

## Key entry points

- `camera.py`: camera controller, ROI storage, snapshot handling, and strobe integration via `strobe_cam.py`
- `strobe_cam.py`: camera/strobe synchronization logic (control mode selection, timing behavior)
- `flow_web.py`: flow/pressure controller wrapper for UI operations
- `heater_web.py`: heater/stirring controller wrapper for UI operations
- `droplet_detector_controller.py`: droplet detection orchestration and performance metrics

## Extension points (how to add features safely)

- **New device module**: create a new controller file here and keep driver-level comms in `../drivers/`.
- **New “mode” or mapping**: centralize shared mappings in `../config.py` where possible to avoid duplication across layers.
- **New UI command**: add WebSocket/HTTP handler in `../rio-webapp/controllers/` and call into these controllers (do not re-implement business logic in the web layer).

## Testing

Run tests from the `software/` directory.
- Routine tests should use simulation mode unless explicitly testing on hardware:

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```


