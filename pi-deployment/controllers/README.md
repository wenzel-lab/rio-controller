# software/controllers/ — Device controllers (hardware orchestration)

This folder contains stateful controllers that coordinate hardware drivers into “things the UI can do” (start camera streaming, set strobe timing, set pressure/flow targets, run heater PID, run droplet detection, etc.).

In the default app entrypoint (`software/main.py`), these controllers are instantiated first, then handed to the web layer (`software/rio-webapp/`) which exposes them via HTTP/WebSocket.

## What belongs here / what does not

- **Belongs here**: long-lived state, orchestration across multiple drivers, “do the safe thing” guardrails, and any cross-cutting timing logic (e.g., camera↔strobe).
- **Does not belong here**: SPI/GPIO packet framing (belongs in `../drivers/`), Flask routing and Socket.IO event registration (belongs in `../rio-webapp/`), and browser JS (belongs in `../rio-webapp/static/`).

## Key controllers and their interfaces

- **`camera.py` — `class Camera`**
  - Owns the camera capture thread and holds the current ROI (`Camera.get_roi()` returns `(x, y, w, h)` or `None`).
  - Owns droplet calibration values (`get_calibration()` / `set_calibration(...)`).
  - Integrates strobe timing via `PiStrobeCam` (see `strobe_cam.py`).
  - Emits UI updates via Socket.IO (event names come from `software/config.py`).
  - ROI modes: software ROI by default; hardware ROI optional via `RIO_ROI_MODE=hardware` when the camera backend supports it (falls back to software if not).

- **`strobe_cam.py` — `class PiStrobeCam`**
  - Composition of `drivers.strobe.PiStrobe` + `drivers.camera.BaseCamera`.
  - Supports two strobe control modes (see `STROBE_CONTROL_MODE` in `software/config.py`):
    - **strobe-centric**: strobe timing is the “clock”
    - **camera-centric**: camera frame callbacks trigger a GPIO pulse to the strobe PIC
  - Exposes camera selection via `set_camera_type(camera_type)`.

- **`flow_web.py` — `class FlowWeb`**
  - Wraps the low-level `drivers.flow.PiFlow` protocol.
  - Tracks per-channel state and performs UI↔firmware control-mode mapping (canonical mapping lives in `flow_control_modes.py` and is re-exported by `config.py`; no local dicts here).
  - Typical calls: `set_pressure(index, mbar)`, `set_flow(index, ul_hr)`, `set_control_mode(index, firmware_mode)`.

- **`heater_web.py` — `class heater_web`**
  - Wraps the low-level `drivers.heater.PiHolder` protocol.
  - Tracks display-ready strings and state flags (`pid_enabled`, `stir_enabled`, `autotuning`).
  - Typical calls: `set_temp(temp_c)`, `set_pid_running(on)`, `set_autotune(on)`, `set_stir_running(on)`, `update()`.

- **`droplet_detector_controller.py` — `class DropletDetectorController` (optional)**
  - Bridges the camera ROI + frames into the algorithm in `../droplet-detection/`.
  - Public surface used by the web layer includes: `start()`, `stop()`, `reset()`, `update_config(dict)`, `load_profile(path)`, `get_histogram()`, `get_statistics()`, `get_performance_metrics()`, `export_data(format="csv"|"txt")`.

## Integration points (who calls these?)

- `software/rio-webapp/controllers/*` call these controllers from Socket.IO handlers.
- `software/rio-webapp/routes.py` exposes a subset via HTTP endpoints (and also emits periodic UI updates).

## Testing

Most tests should run in simulation mode (no physical hardware required):

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change controller behavior, public methods, or event/API contracts, update this document.


