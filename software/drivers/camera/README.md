# software/drivers/camera/ — Camera abstraction + backends

This folder provides a single camera interface (`BaseCamera`) for the rest of the app, plus several concrete backends (Pi camera variants and an Allied Vision Mako backend).

The primary consumer is `software/controllers/strobe_cam.py` (via `drivers.camera.create_camera(...)`), which then feeds frames into the web UI and optional droplet detection.

## Public interface (`camera_base.py`)

`camera_base.py` defines:

- **`class BaseCamera`** (abstract)
  - lifecycle: `start()` / `stop()` / `close()`
  - streaming: `generate_frames(...) -> generator[bytes]` (MJPEG-style)
  - numpy access: `get_frame_array() -> np.ndarray` (RGB)
  - ROI access: `get_frame_roi((x, y, w, h)) -> np.ndarray` (RGB)
  - configuration: `set_config(dict)` (keys vary by backend, but width/height/fps are common)
  - strobe integration hook: `set_frame_callback(callback)` (called per frame in camera-centric strobe mode)
  - optional UI helpers: `list_features()` and backend-specific helpers like ROI constraints

- **`create_camera(camera_type=None, simulation=False, sim_config=None)`**
  - selects a backend based on:
    - `RIO_SIMULATION=true` → simulated camera (`software/simulation/camera_simulated.py`)
    - requested `camera_type` (`"mako"`, `"rpi"`, `"rpi_hq"`, `"none"`)
    - platform/library availability (picamera2 vs picamera)

## Backends (what each file provides)

- `pi_camera_v2.py`
  - Raspberry Pi camera backend built on `picamera2` (typical for 64-bit Pi OS)
  - expected to implement ROI extraction and expose camera controls/features for the UI

- `pi_camera_legacy.py`
  - Raspberry Pi camera backend built on legacy `picamera` (commonly 32-bit / older systems)

- `mako_camera.py`
  - Allied Vision Mako backend (Vimba stack)
  - often has stricter constraints and different feature/ROI capabilities than Pi camera backends

## ROI in this layer

The interface supports **software ROI** via `get_frame_roi((x, y, w, h))`.
Some backends also include “hardware ROI” helpers (sensor/stream crop), but *choosing* between software vs hardware ROI is an application policy decision (typically owned by higher layers).
- Hardware ROI support: `pi_camera_v2` (picamera2) and `pi_camera_legacy` (picamera) implement `set_roi_hardware`; `mako_camera` exposes it via Vimba. If a backend rejects hardware ROI, callers should fall back to software ROI.

## Testing

From `software/` (simulation mode unless explicitly testing on hardware):

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change camera interfaces, selection rules, or ROI semantics, update this document.


