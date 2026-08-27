# software/drivers/camera/ — Camera abstraction + backends

This folder provides a single camera interface (`BaseCamera`) for the rest of the app, plus several concrete backends (Pi camera variants and USB3 backends like Mako and Daheng).

The primary consumer is `software/controllers/strobe_cam.py` (via `drivers.camera.create_camera(...)`), which then feeds frames into the web UI and optional droplet detection.

## Public interface (`camera_base.py`)

`camera_base.py` defines:

- **`class BaseCamera`** (abstract)
  - lifecycle: `start()` / `stop()` / `close()`
  - streaming: `generate_frames(...) -> generator[bytes]` (MJPEG-style)
  - numpy access: `get_frame_array() -> np.ndarray` (RGB)
  - ROI access: `get_frame_roi((x, y, w, h)) -> np.ndarray` (RGB)
  - configuration: `set_config(dict)` (keys vary by backend, but width/height/fps are common)
  - strobe integration hook: `set_frame_callback(callback)` (reserved for future trigger-based modes)
  - optional UI helpers: `list_features()` and backend-specific helpers like ROI constraints

- **`create_camera(camera_type=None, simulation=False, sim_config=None)`**
  - selects a backend based on:
    - `RIO_SIMULATION=true` → simulated camera (`software/simulation/camera_simulated.py`)
- requested `camera_type` (`"mako"`, `"daheng"`, `"rpi"`, `"none"`)
- platform/library availability (picamera, gxipy, vimba)

## Backends (what each file provides)

  - expected to implement ROI extraction and expose camera controls/features for the UI

- `pi_camera_legacy.py`
  - Raspberry Pi camera backend built on legacy `picamera` (commonly 32-bit / older systems)

- `mako_camera.py`
  - Allied Vision Mako backend (Vimba stack)
  - often has stricter constraints and different feature/ROI capabilities than Pi camera backends

- `daheng_camera.py`
  - Daheng MER2 backend via **Python gxipy** (Galaxy SDK)
  - requires vendor SDK + Python bindings on the host
  - optional env: `RIO_DAHENG_SN` (open by serial) or `RIO_DAHENG_INDEX` (0-based index)
  - default path when `RIO_DAHENG_CPP` is unset / off

- `daheng_cpp_camera.py` + `daheng_cpp_grabber.py` + `software/native/daheng_grabber/`
  - optional **native C++** Acq path (`GXDQAllBufs`, GxViewer-style drain)
  - enable with `RIO_DAHENG_CPP=1` (preferred on Ubuntu host + MER2 when high Acq.FPS matters)
  - open loads Galaxy **UserSet Default** (stable live preview: AE Off, default exposure/gain from the device profile)
  - build `libdaheng_grabber.so` with system/conda **g++** (not Zig) — see [`native/daheng_grabber/README.md`](../../native/daheng_grabber/README.md)
  - UI Disp ~30 FPS is independent of Acq; more notes: [`docs/daheng-cpp-galaxy-notes.md`](../../docs/daheng-cpp-galaxy-notes.md)
  - related branches (history): `feature/daheng-cpp-acq-grabber`, `feature/daheng-python-acq-ab`

### Daheng host env (quick)

```bash
export GALAXY_ROOT="$HOME/Galaxy_camera"
export LD_LIBRARY_PATH="$GALAXY_ROOT/lib/x86_64:$LD_LIBRARY_PATH"
export RIO_CAMERA_TYPE=daheng
export RIO_DAHENG_SN=<serial>          # optional
export RIO_DAHENG_CPP=1                # native grabber; omit for gxipy-only
# optional: RIO_DAHENG_EXPOSURE_US=1000  RIO_DAHENG_AFR_MAX=1
```

Hardware ROI support: `pi_camera_legacy` (picamera) implements `set_roi_hardware`; `mako_camera` exposes it via Vimba; `daheng_camera` / `daheng_cpp_camera` expose it via gxipy / native grabber. If a backend rejects hardware ROI, callers should fall back to software ROI.

**ROI invariants (all backends):**
- ROI coordinates are pixel-based and refer to the current stream frame.
- If hardware ROI is active and matches the requested ROI, the returned frame is already cropped (full frame == ROI).
- If hardware ROI is active but does not match, callers should treat ROI as software cropping on the decoded frame.

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
- Updated: 2026-08-11 — documented optional `RIO_DAHENG_CPP` native grabber vs gxipy.


