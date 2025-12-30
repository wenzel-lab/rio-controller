## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change behavior or public interfaces, please update this document.

## Purpose

This folder implements the **camera abstraction layer** used by the rest of the application. It provides a common interface (`BaseCamera`) and multiple camera backends (Pi cameras and Allied Vision Mako).

## Key files

- `camera_base.py`: `BaseCamera` interface and `create_camera()` factory
- `pi_camera_v2.py`: Pi camera implementation using `picamera2` (64-bit OS)
- `pi_camera_legacy.py`: Pi camera implementation using `picamera` (legacy / typically 32-bit)
- `mako_camera.py`: Mako camera implementation using Vimba

## What belongs here / what does not

- **Belongs here**:
  - camera start/stop, frame generation, and conversion to formats used by the rest of the system
  - ROI helpers (software cropping) and camera-specific ROI constraints
  - camera feature listing (for UI configuration panels)
- **Does not belong here**:
  - WebSocket events, Flask routes, template formatting (belongs in `../../rio-webapp/`)
  - high-level system orchestration (belongs in `../../controllers/`)

## ROI notes (high level)

The interface exposes `get_frame_roi((x, y, w, h))` for ROI extraction. Some camera backends also implement “hardware ROI” helpers (sensor/stream ROI), but whether hardware ROI is enabled is decided by higher layers (device controllers).

## Testing

Run tests from `software/` (simulation mode unless explicitly testing on hardware):

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```


