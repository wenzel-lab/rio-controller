# software/api/ — Network API layer (FastAPI + WebSockets)

This folder contains the **network API layer** that exposes Rio hardware control and telemetry over HTTP/REST and WebSockets. It is designed to run alongside the existing Flask UI (`../rio-webapp/`) and provides a machine-readable interface for Jupyter notebooks, scripts, and external applications.

**✅ Web of Things (WoT) Compatible:** The API uses **LabThings FastAPI** to expose controllers as WoT-compliant Things.

- Controllers are wrapped as LabThings Things (FlowThing, HeaterThing, CameraThing, etc.)
- Auto-generated Thing Descriptions (TD) for each Thing
- Standard WoT properties, actions, and events
- OpenAPI/Swagger documentation + Thing Description JSON
- Custom endpoints remain at `/api/` prefix for backward compatibility

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
   Optional pump enable (USB serial):
   ```bash
   export RIO_PUMP_ENABLED=true
   # export RIO_PUMP_PORT=/dev/ttyUSB0
   ```

3. **Test the API:**
   ```bash
   curl http://localhost:8000/api/system/health
   # Or test WoT Thing:
   curl http://localhost:8000/flow/
   ```

4. **View API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Thing Descriptions: http://localhost:8000/thing_descriptions/
   - Individual Thing: http://localhost:8000/flow/ (FlowThing TD)

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
   Optional pump enable (USB serial):
   ```bash
   export RIO_PUMP_ENABLED=true
   # export RIO_PUMP_PORT=/dev/ttyUSB0
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
   from api.client import RioClient
   client = RioClient(base_url="http://raspberrypi.local:8000")
   health = client.health()
   print(health)
   ```

**For detailed Pi installation and Jupyter access guide, see:** `../../docs/api_pi_testing_guide.md`

See `client/README.md` for the Python client library and example notebooks.

## What belongs here / what does not

- **Belongs here**: LabThings Thing classes, ThingServer setup, WebSocket handlers, request/response schemas (Pydantic models), API configuration, and streaming aggregators.
- **Does not belong here**: Hardware drivers (belongs in `../drivers/`), device controllers (belongs in `../controllers/`), Flask routes (belongs in `../rio-webapp/`), and browser JavaScript (belongs in `../rio-webapp/static/`).

## Architecture and integration

The API layer sits **above** the device controllers (`../controllers/`) and **below** client applications (Jupyter notebooks, scripts, external UIs). It follows the same architectural pattern as the Flask UI:

```
┌─────────────────────────────────────┐
│  Client (Jupyter/script/external)  │
└──────────────┬──────────────────────┘
               │ HTTP/REST + WebSocket
┌──────────────▼──────────────────────┐
│  software/api/ (this folder)         │
│  - LabThings ThingServer (WoT)      │
│  - Thing classes (FlowThing, etc.)   │
│  - WebSocket aggregator              │
│  - Request/response schemas          │
│  - Legacy /api/control/* routes      │
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

### `main.py` — LabThings ThingServer and routes

- **Entry point**: `create_app()` returns a FastAPI instance with LabThings ThingServer integration.
- **Controller initialization**: Controllers are instantiated at import time (similar to `software/main.py`) so capabilities reflect actual hardware availability.
- **WoT Things** (auto-generated routes by LabThings):
  - `/flow/` — FlowThing (flow/pressure control)
  - `/heater/` — HeaterThing (heater control)
  - `/camera/` — CameraThing (camera and strobe control)
  - `/droplet/` — DropletThing (droplet detection)
  - `/pump/` — PumpThing (placeholder for future pump support)
- **Custom endpoints** (backward compatibility):
  - `/api/system/health` — Health check
  - `/api/system/capabilities` — Available modules
  - `/api/config/channels` — Channel metadata (names, liquid types, calibration factors)
  - `/api/streams/aggregate` — WebSocket aggregator for sensor data
  - `/api/data/capture/*` — On-demand CSV capture control
- **WoT endpoints** (auto-generated):
  - `/thing_descriptions/` — All Thing Descriptions
  - `/docs` — OpenAPI/Swagger UI
  - `/openapi.json` — OpenAPI specification

### `things/` — LabThings Thing classes

WoT-compliant Thing classes that wrap controllers:
- **`flow_thing.py`**: FlowThing — flow/pressure control (properties: `state`, actions: `set_pressure`, `set_flow`, `set_mode`, `set_pi_consts`)
- **`heater_thing.py`**: HeaterThing — heater control (properties: `state`, actions: `set_temp`, `set_pid`, `set_stir`)
- **`camera_thing.py`**: CameraThing — camera/strobe control (actions: `snapshot`, `set_resolution`, `set_roi`, `strobe_enable`, etc.)
- **`droplet_thing.py`**: DropletThing — droplet detection (properties: `status`, `statistics`, `histogram`, actions: `start`, `stop`)
- **`pump_thing.py`**: PumpThing — placeholder for future pump support

Each Thing exposes:
- **Properties**: Readable state (e.g., `GET /flow/state`)
- **Actions**: Invocable methods (e.g., `POST /flow/set_pressure`)
- **Thing Description**: Machine-readable WoT TD at `/flow/`, `/heater/`, etc.

### `schemas.py` — Request/response models

Pydantic models for API requests and responses. Used by both Things and custom endpoints:
- **Type validation**: Automatic validation of request bodies and query parameters
- **OpenAPI documentation**: FastAPI auto-generates OpenAPI/Swagger docs from these models
- **Thing Descriptions**: LabThings uses these models in WoT TD generation
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
- `POST /api/control/heater/power_limit` — Set heater power limit (%)
- `POST /api/control/heater/autotune` — Start/stop autotune

### Camera/Strobe control
- `GET /api/streams/camera/snapshot` — Get JPEG snapshot
- `POST /api/control/camera/set_resolution` — Set display resolution
- `POST /api/control/camera/set_snapshot_resolution` — Set snapshot resolution mode
- `POST /api/control/camera/roi` — Set ROI
- `POST /api/control/camera/roi/clear` — Clear ROI
- `GET /api/control/camera/state` — Get camera state (for remote UI)
- `POST /api/control/camera/select` — Select camera backend
- `POST /api/control/strobe/enable` — Enable/disable strobe
- `POST /api/control/strobe/hold` — Enable/disable hold mode
- `POST /api/control/strobe/timing` — Set strobe timing (period, wait)
- `GET /api/control/strobe/state` — Get strobe state (for remote UI)

### Droplet detection
- `POST /api/control/droplet/start` — Start detection
- `POST /api/control/droplet/stop` — Stop detection
- `GET /api/control/droplet/status` — Get status
- `GET /api/control/droplet/histogram` — Get histogram
- `GET /api/control/droplet/statistics` — Get statistics
- `GET /api/control/droplet/performance` — Get performance metrics

### Pump control (USB serial)
- `GET /api/control/pump/state/{pump}` — Get pump state
- `POST /api/control/pump/set_flow` — Set flow
- `POST /api/control/pump/set_diameter` — Set diameter
- `POST /api/control/pump/set_direction` — Set direction (infuse/withdraw)
- `POST /api/control/pump/set_state` — Start/stop
- `POST /api/control/pump/set_unit` — Set unit
- `POST /api/control/pump/set_gearbox` — Set gearbox
- `POST /api/control/pump/set_microstep` — Set microstep
- `POST /api/control/pump/set_threadrod` — Set threadrod
- `POST /api/control/pump/set_enable` — Enable/disable

### Streaming and capture
- `WS /api/streams/aggregate` — WebSocket aggregator (flow/pressure/heater telemetry)
- `POST /api/data/capture/start` — Start CSV capture
- `POST /api/data/capture/stop` — Stop CSV capture
- `GET /api/data/capture/status` — Get capture status

## Client examples

### Python client library

A lightweight client library is available at `client/api_client.py`:
- `RioClient` — REST API client with error handling and retry logic
- `RioStreamClient` — WebSocket aggregator client with thread-safe message queue

Example usage:
```python
from api.client import RioClient, RioStreamClient

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

See `client/README.md` for complete documentation.

### Jupyter notebooks

Two example notebooks are available in `software/api/client/notebooks/` (repo root path):

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

### Testing with Jupyter Notebooks in Simulation Mode

To test the API using Jupyter notebooks in simulation mode (without hardware):

1. **Start the API server in simulation mode** (in a terminal):
   ```bash
   cd software
   export RIO_SIMULATION=true
   python -m api.main
   ```
   The server will start on `http://localhost:8000`. You should see:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

2. **Install Jupyter** (if not already installed in your environment):
   ```bash
   pip install jupyter jupyterlab ipywidgets matplotlib pandas numpy
   ```

3. **Open a Jupyter notebook** (in a new terminal, same environment):
   ```bash
   cd software
   # Make sure you're in the same environment (rio-simulation)
   mamba activate rio-simulation  # if not already activated
   jupyter notebook
   ```
   Or use JupyterLab:
   ```bash
   jupyter lab
   ```

3. **Navigate to the client notebooks**:
   - Open `api/client/notebooks/tutorial.ipynb` or `api/client/notebooks/interactive_control.ipynb`
   - Or create a new notebook

4. **Set up the client in the notebook**:
   ```python
   import sys
   # Add client library to path
   sys.path.insert(0, '/path/to/rio-controller/software')
   
   from api.client import RioClient, RioStreamClient
   
   # Connect to local API server
   API_BASE_URL = "http://localhost:8000"
   client = RioClient(base_url=API_BASE_URL)
   
   # Test connection
   health = client.health()
   print(f"API Status: {health['status']}")
   print(f"Simulation Mode: {health['simulation']}")
   ```

5. **Run the notebook cells**:
   - The notebooks will work with the simulation API
   - Flow, pressure, and heater controllers will use simulated hardware
   - Camera will use simulated frames (synthetic droplets)
   - All API endpoints are available and functional

**Note**: Keep the API server running in the terminal while using the notebook. If you stop the server, restart it and the notebook will reconnect automatically.

**Troubleshooting**:
- **Connection refused**: Make sure the API server is running (`python -m api.main`)
- **Module not found**: Make sure `software/` is in your Python path (see step 4)
- **Import errors**: Install client dependencies: `pip install requests websocket-client`
- **Notebook dependencies**: For plotting and widgets: `pip install matplotlib pandas numpy ipywidgets`

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
- `fastapi[all]>=0.115.0` — Web framework (supports Pydantic 2.x)
- `uvicorn[standard]>=0.30.0` — ASGI server (compatible with FastAPI 0.115+)
- `labthings-fastapi>=0.0.6` — **LabThings/WoT framework** (requires Pydantic 2.x)
- `pydantic>=2.10.0` — Data validation (Pydantic 2.x, required by LabThings)
- `pyyaml>=6.0` — Config file loading

**Current status:** The API uses LabThings ThingServer to expose controllers as WoT-compliant Things. Each controller is wrapped in a Thing class that exposes properties and actions according to the Web of Things standard.

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
from api.client import RioClient
client = RioClient(base_url="http://192.168.1.100:8000")
client.set_flow(0, 100.0)  # Set channel 0 to 100 ul/hr
```

**Monitor sensors in real-time:**
```python
from api.client import RioStreamClient
stream = RioStreamClient(base_url="http://192.168.1.100:8000")
stream.subscribe(["flow", "pressure"])
for msg in stream.iter_messages(timeout=60.0):
    print(f"{msg['topic']} ch{msg['channel']}: {msg['value']} {msg['unit']}")
```

**Capture data to CSV:**
```python
from api.client import RioClient
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

- **Authentication**: Token-based or basic auth for LAN security
- **Remote adapters**: Configuration-driven split-host deployment (Pi + external PC)
- **Pump driver**: Implement syringe pump driver/controller to enable PumpThing
- **UI adapters**: Flask UI calls API instead of controllers directly (single-owner rule)
- **ThingClient migration**: Update client library to use LabThings ThingClient for auto-generated clients

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-01-XX
- Maintenance: If you change API routes, schemas, or behavior, update this document.

