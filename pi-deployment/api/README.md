# software/api/ — Network API layer (FastAPI + WebSockets)

This folder contains the **network API layer** that exposes Rio hardware control and telemetry over HTTP/REST and WebSockets. It is designed to run alongside the existing Flask UI (`../rio-webapp/`) and provides a machine-readable interface for Jupyter notebooks, scripts, and external applications.

**⚠️ Important:** The API currently uses **plain FastAPI** (standard REST endpoints). It is **NOT Web of Things (WoT) compatible**. 

- `labthings-fastapi` is installed as a dependency but **not used** in the code
- The API uses standard FastAPI routes (`@app.get`, `@app.post`, etc.)
- No LabThings "Things", "Properties", "Actions", or "Events" are exposed
- WoT compatibility is planned as a future enhancement (see "Future enhancements" section)

## Quick Start

### Development Setup (Mac/PC)

1. **Install dependencies:**
   ```bash
   cd software
   pip install -r requirements-api.txt
   ```

2. **Run the API server:**
   ```bash
   # Development (with auto-reload)
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   
   # Or directly
   python -m api.main
   ```

3. **Test the API:**
   ```bash
   curl http://localhost:8000/api/system/health
   ```

4. **View API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Raspberry Pi Deployment

**Prerequisites:** Base requirements (`requirements-pi.txt`) must be installed first.

1. **Install API dependencies on Pi:**
   ```bash
   cd ~/rio-controller
   python3 -m pip install --user -r requirements-api.txt
   ```

2. **Launch API server:**
   ```bash
   cd ~/rio-controller
   export RIO_SIMULATION=false
   python3 -m api.main
   ```

3. **Test from Pi:**
   ```bash
   curl http://localhost:8000/api/system/health
   ```

4. **Test from your computer:**
   ```bash
   # Replace with your Pi's IP or hostname
   curl http://raspberrypi.local:8000/api/system/health
   ```

5. **Access from Jupyter notebook:**
   ```python
   from client import RioClient
   client = RioClient(base_url="http://raspberrypi.local:8000")
   health = client.health()
   print(health)
   ```

**For detailed Pi installation and Jupyter access guide, see:** `../../docs/api_pi_testing_guide.md`

See `../client/README.md` for the Python client library and example notebooks.

## What belongs here / what does not

- **Belongs here**: FastAPI routes, WebSocket handlers, request/response schemas (Pydantic models), API configuration, and streaming aggregators.
- **Does not belong here**: Hardware drivers (belongs in `../drivers/`), device controllers (belongs in `../controllers/`), Flask routes (belongs in `../rio-webapp/`), and browser JavaScript (belongs in `../rio-webapp/static/`).

## Architecture and integration

The API layer sits **above** the device controllers (`../controllers/`) and **below** client applications (Jupyter notebooks, scripts, external UIs). It follows the same architectural pattern as the Flask UI:

```
┌─────────────────────────────────────┐
│  Client (Jupyter/script/external)  │
└──────────────┬──────────────────────┘
               │ HTTP/REST + WebSocket
┌──────────────▼──────────────────────┐
│  software/api/ (this folder)        │
│  - FastAPI routes                    │
│  - WebSocket aggregator              │
│  - Request/response schemas          │
└──────────────┬──────────────────────┘
               │ Controller methods
┌──────────────▼──────────────────────┐
│  software/controllers/              │
│  - FlowWeb, heater_web, Camera, etc.│
└──────────────┬──────────────────────┘
               │ Driver protocols
┌──────────────▼──────────────────────┐
│  software/drivers/                  │
│  - PiFlow, PiHolder, PiStrobe, etc. │
└─────────────────────────────────────┘
```

The API **does not** call drivers directly; it calls into the controller layer, which ensures proper state management, safety guardrails, and consistent behavior with the Flask UI.

## Key components

### `main.py` — FastAPI application and routes

- **Entry point**: `create_app()` returns a FastAPI instance with all routes registered.
- **Controller initialization**: Controllers are instantiated at import time (similar to `software/main.py`) so capabilities reflect actual hardware availability.
- **REST endpoints**:
  - `/api/system/health` — Health check
  - `/api/system/capabilities` — Available modules
  - `/api/config/channels` — Channel metadata (names, liquid types, calibration factors)
  - `/api/control/flow/*` — Flow/pressure control
  - `/api/control/heater/*` — Heater control
  - `/api/control/camera/*` — Camera control (resolution, ROI, snapshot)
  - `/api/control/strobe/*` — Strobe control (enable, hold, timing)
  - `/api/control/droplet/*` — Droplet detection control
  - `/api/control/pump/*` — Syringe pump control (placeholder, returns 501 until driver implemented)
  - `/api/streams/camera/snapshot` — JPEG snapshot endpoint
  - `/api/data/capture/*` — On-demand CSV capture control

### `schemas.py` — Request/response models

Pydantic models for all API requests and responses. These provide:
- **Type validation**: Automatic validation of request bodies and query parameters
- **OpenAPI documentation**: FastAPI auto-generates OpenAPI/Swagger docs from these models
- **Clear contracts**: Explicit data structures for clients

Key models:
- `FlowState`, `FlowSetPressureRequest`, `FlowSetFlowRequest`, etc.
- `HeaterState`, `HeaterSetTempRequest`, etc.
- `ChannelConfig`, `ChannelMetadata` (for channel naming/liquid types)
- `CaptureStartRequest`, `CaptureStatusResponse` (for data capture)
- Camera/strobe/droplet/pump request models

### `streams.py` — WebSocket aggregator and data capture

- **`Aggregator` class**: Multiplexes multiple sensor streams (flow, pressure, heater) over a single WebSocket connection.
- **Channel selection**: Clients can subscribe to specific channels per topic (e.g., only flow channels 0 and 2).
- **Calibration factors**: Applies calibration factors from config YAML to flow/pressure values.
- **On-demand capture**: Optional CSV logging of streamed data (disabled by default, enabled via `/api/data/capture/start`).

WebSocket endpoint: `/api/streams/aggregate`

Message format:
```json
{
  "topic": "flow",
  "channel": 0,
  "timestamp": 1234567890.123,
  "value": 100.5,
  "unit": "ul_hr"
}
```

### `config.py` — API configuration

Settings for:
- Host/port (default: `0.0.0.0:8000`)
- CORS (default: allow all origins)
- Simulation mode detection
- Stream rates and buffer sizes

## Running the API server

### Standalone (development/testing)

```bash
cd software
export RIO_SIMULATION=true  # Optional: run without hardware
python -m api.main
```

Or use uvicorn directly:
```bash
cd software
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Alongside Flask UI (production)

The API and Flask UI can run in parallel, but only **one process should own hardware** per module. Configuration-driven "single-owner" rules (future) will prevent conflicts.

Current approach: API is the hardware owner; Flask UI uses adapters (future step) or runs on a different host.

### Configuration

Channel metadata (names, liquid types, calibration factors) is loaded from the main config file:
- Default: `rio-config.yaml` in `software/`
- Override: `RIO_CONFIG_FILE` environment variable

Example config structure:
```yaml
channels:
  flow:
    "0":
      name: "oil"
      liquid_type: "mineral_oil"
      calibration_factor: 1.05
    "1":
      name: "cells"
      liquid_type: "aqueous"
      calibration_factor: 1.0
```

## API endpoints overview

### System
- `GET /api/system/health` — Health check
- `GET /api/system/capabilities` — Available modules

### Configuration
- `GET /api/config/channels` — Get channel metadata
- `POST /api/config/channels` — Update channel metadata (runtime-only, not persisted)

### Flow/Pressure control
- `GET /api/control/flow/state` — Get current state (targets, actuals, modes)
- `POST /api/control/flow/set_pressure` — Set pressure target (mbar)
- `POST /api/control/flow/set_flow` — Set flow target (ul/hr)
- `POST /api/control/flow/set_mode` — Set control mode
- `POST /api/control/flow/set_pi_consts` — Set PI controller constants

### Heater control
- `GET /api/control/heater/state` — Get heater states
- `POST /api/control/heater/set_temp` — Set target temperature
- `POST /api/control/heater/pid` — Enable/disable PID
- `POST /api/control/heater/stir` — Enable/disable stirrer

### Camera/Strobe control
- `GET /api/streams/camera/snapshot` — Get JPEG snapshot
- `POST /api/control/camera/set_resolution` — Set display resolution
- `POST /api/control/camera/set_snapshot_resolution` — Set snapshot resolution mode
- `POST /api/control/camera/roi` — Set ROI
- `POST /api/control/camera/roi/clear` — Clear ROI
- `POST /api/control/strobe/enable` — Enable/disable strobe
- `POST /api/control/strobe/hold` — Enable/disable hold mode
- `POST /api/control/strobe/timing` — Set strobe timing (period, wait)

### Droplet detection
- `POST /api/control/droplet/start` — Start detection
- `POST /api/control/droplet/stop` — Stop detection
- `GET /api/control/droplet/status` — Get status
- `GET /api/control/droplet/histogram` — Get histogram
- `GET /api/control/droplet/statistics` — Get statistics
- `GET /api/control/droplet/performance` — Get performance metrics

### Pump control (placeholder)
- `GET /api/control/pump/state/{pump}` — Get pump state (returns 501)
- `POST /api/control/pump/set_flow` — Set flow (returns 501)
- `POST /api/control/pump/set_diameter` — Set diameter (returns 501)
- ... (all pump endpoints return 501 until driver implemented)

### Streaming and capture
- `WS /api/streams/aggregate` — WebSocket aggregator (flow/pressure/heater telemetry)
- `POST /api/data/capture/start` — Start CSV capture
- `POST /api/data/capture/stop` — Stop CSV capture
- `GET /api/data/capture/status` — Get capture status

## Client examples

### Python client library

A lightweight client library is available at `../client/api_client.py`:
- `RioClient` — REST API client with error handling and retry logic
- `RioStreamClient` — WebSocket aggregator client with thread-safe message queue

Example usage:
```python
from client import RioClient, RioStreamClient

# REST client
client = RioClient(base_url="http://192.168.1.100:8000")
state = client.get_flow_state()
client.set_flow(0, 100.0)  # Set channel 0 to 100 ul/hr

# WebSocket client
stream = RioStreamClient(base_url="http://192.168.1.100:8000")
stream.subscribe(["flow"], channels={"flow": [0, 1]})
for msg in stream.iter_messages(timeout=10.0):
    print(f"{msg['topic']}: {msg['value']}")
```

See `../client/README.md` for complete documentation.

### Jupyter notebooks

Two example notebooks are available in `../client/notebooks/`:

1. **`tutorial.ipynb`** — Step-by-step learning notebook:
   - REST API control (flow, heater, camera)
   - WebSocket telemetry streaming with batching
   - On-demand data capture
   - Data visualization

2. **`interactive_control.ipynb`** — Interactive UI with ipywidgets:
   - Real-time control sliders
   - Live status updates
   - Camera snapshot capture
   - Emergency stop button

## Testing

API tests are in `../tests/test_api_streams.py`. Run with:

```bash
cd software
export RIO_SIMULATION=true
pytest tests/test_api_streams.py -v
```

Note: API tests require `requirements-api.txt` to be installed. Install with:
```bash
pip install -r requirements-api.txt
```

## OpenAPI/Swagger documentation

FastAPI automatically generates OpenAPI documentation. When the API server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Dependencies

API-specific dependencies are in `requirements-api.txt`:
- `fastapi==0.95.2` — Web framework (currently using plain FastAPI, not LabThings)
- `uvicorn[standard]==0.21.1` — ASGI server
- `labthings-fastapi==0.0.6` — **Installed but not used** (for future WoT integration)
- `pydantic==1.10.14` — Data validation
- `pyyaml` — Config file loading

**Current status:** The API uses standard FastAPI routes and does not expose LabThings "Things", "Properties", "Actions", or "Events". The `labthings-fastapi` package is included for future migration to WoT-compliant endpoints.

Install with:
```bash
pip install -r requirements-api.txt
```

## Troubleshooting

### API server won't start

**"Address already in use"**:
- Another process is using port 8000
- Find and kill: `lsof -ti:8000 | xargs kill -9`
- Or use a different port: `uvicorn api.main:app --port 8001`

**"Module not found"**:
- Install dependencies: `pip install -r requirements-api.txt`
- Make sure you're running from `software/` directory
- Check Python path: `python -c "import api.main"`

### Controllers not available

**"Controller unavailable" (503 errors)**:
- Check capabilities: `GET /api/system/capabilities`
- Verify hardware is connected (or simulation mode is enabled)
- Check controller initialization logs for errors
- In simulation mode: `export RIO_SIMULATION=true`

### WebSocket connection fails

**"WebSocket connection failed"**:
- Verify API server is running
- Check firewall/network settings
- Ensure WebSocket endpoint is accessible: `ws://<host>:8000/api/streams/aggregate`
- Check browser console or client logs for errors

### Common use cases

**Control flow from script:**
```python
from client import RioClient
client = RioClient(base_url="http://192.168.1.100:8000")
client.set_flow(0, 100.0)  # Set channel 0 to 100 ul/hr
```

**Monitor sensors in real-time:**
```python
from client import RioStreamClient
stream = RioStreamClient(base_url="http://192.168.1.100:8000")
stream.subscribe(["flow", "pressure"])
for msg in stream.iter_messages(timeout=60.0):
    print(f"{msg['topic']} ch{msg['channel']}: {msg['value']} {msg['unit']}")
```

**Capture data to CSV:**
```python
from client import RioClient
client = RioClient(base_url="http://192.168.1.100:8000")
client.capture_start(["flow", "pressure"], path="experiment.csv")
# ... run experiment ...
client.capture_stop()
```

## Performance considerations

- **Streaming rates**: WebSocket supports 20-50 Hz per channel. Higher rates may require client-side decimation.
- **Buffer sizes**: Message queue defaults to 1000 messages. Adjust with `RioStreamClient(max_queue_size=...)`.
- **Concurrent connections**: Multiple clients can connect simultaneously. Each WebSocket connection is independent.
- **CPU usage**: Streaming 4 channels at 50 Hz uses minimal CPU. Camera streaming is more intensive.

## Future enhancements

- **LabThings/WoT integration**: Expose Things, Properties, Actions, Events (WoT-compliant)
- **Authentication**: Token-based or basic auth for LAN security
- **Remote adapters**: Configuration-driven split-host deployment (Pi + external PC)
- **Pump driver**: Implement syringe pump driver/controller to enable pump endpoints
- **UI adapters**: Flask UI calls API instead of controllers directly (single-owner rule)

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-01-XX
- Maintenance: If you change API routes, schemas, or behavior, update this document.

