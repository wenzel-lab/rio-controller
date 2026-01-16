# software/api/client/ — Rio API Client Library

This folder contains the **Python client library** for interacting with the Rio controller API. It provides both REST API and WebSocket streaming clients, along with example Jupyter notebooks.

**Two client implementations are available:**

1. **`RioClient`** — Direct HTTP client using `requests` (simple, fast)
   - Uses legacy routes (`/api/control/*`)
   - Synchronous responses (no polling)
   - Fast (10-50ms per action)

2. **`RioThingClient`** — WoT-compliant client using LabThings ThingClient (standard, auto-generated)
   - Uses WoT routes (`/flow/`, `/heater/`, etc.)
   - Auto-generated from Thing Descriptions
   - Async action polling (50-150ms per action, but WoT-compliant)

**Both clients provide the same interface** — you can switch between them easily. Use `RioThingClient` for WoT compliance, or `RioClient` for maximum speed.

## What's inside

- **`api_client.py`**: Python client library (`RioClient` for REST, `RioStreamClient` for WebSocket)
- **`notebooks/`**: Example Jupyter notebooks
  - `tutorial.ipynb`: Step-by-step learning notebook
  - `interactive_control.ipynb`: Interactive UI with ipywidgets

## Quick Start

### Installation

**On your computer (for accessing Pi API):**

The client library requires:
```bash
pip install requests websocket-client
```

For Jupyter notebooks, also install:
```bash
pip install ipywidgets matplotlib pandas numpy jupyter
```

**Note:** The client library code is in `software/api/client/api_client.py`. You can either:
- Import directly if `software/` is in your Python path
- Copy `api_client.py` to your project
- Add `software/` to `PYTHONPATH`

### Basic Usage

**Connecting to Pi API from your computer:**

```python
import sys
# Add client library to path (adjust path to your rio-controller repository)
sys.path.insert(0, '/path/to/rio-controller/software')

from api.client import RioClient, RioStreamClient

# REST API client (replace with your Pi's IP or hostname)
PI_ADDRESS = "raspberrypi.local"  # or "192.168.1.100"
API_URL = f"http://{PI_ADDRESS}:8000"

client = RioClient(base_url=API_URL)

# Check health
health = client.health()
print(f"Status: {health['status']}")

# Get flow state
state = client.get_flow_state()
print(f"Flow channel 0: {state['flow_actuals_ul_hr'][0]} ul/hr")

# Set flow rate
client.set_flow(0, 100.0)  # Set channel 0 to 100 ul/hr

# WebSocket streaming
stream = RioStreamClient(base_url=API_URL)
stream.subscribe(["flow"], channels={"flow": [0, 1]})

for msg in stream.iter_messages(timeout=10.0):
    print(f"{msg['topic']} channel {msg['channel']}: {msg['value']}")
```

**For local development (API on same machine):**
```python
client = RioClient(base_url="http://localhost:8000")
```

### Context Manager

The clients support context managers for automatic cleanup:

```python
with RioClient(base_url="http://localhost:8000") as client:
    state = client.get_flow_state()
    # Session automatically closed on exit

with RioStreamClient(base_url="http://localhost:8000") as stream:
    stream.subscribe(["flow"])
    for msg in stream.iter_messages(timeout=5.0):
        print(msg)
    # WebSocket automatically closed on exit
```

## API Client (`RioClient`)

### Error Handling

The client raises custom exceptions:

- `RioAPIError`: Base exception for all API errors
- `RioConnectionError`: Connection failures (network, timeout)
- `RioHTTPError`: HTTP errors (4xx, 5xx) with status code and response details
- `RioWebSocketError`: WebSocket connection failures

Example:
```python
from api.client import RioClient, RioConnectionError, RioHTTPError

try:
    client = RioClient(base_url="http://192.168.1.100:8000")
    client.set_flow(0, 100.0)
except RioConnectionError as e:
    print(f"Connection failed: {e}")
except RioHTTPError as e:
    print(f"HTTP {e.status_code}: {e.response}")
```

### Retry Logic

The client automatically retries transient failures (timeouts, connection errors) up to 3 times by default. Configure with:

```python
client = RioClient(base_url="...", max_retries=5)
```

### Available Methods

**Note:** All methods use legacy `/api/control/*` routes for backward compatibility. WoT routes are available at `/flow/`, `/heater/`, etc. (see API docs).

**System:**
- `health()` - Get API health status
- `capabilities()` - Get available modules

**Channel Configuration:**
- `get_channels()` - Get channel metadata
- `set_channels(config)` - Update channel metadata

**Flow/Pressure:**
- `get_flow_state()` - Get current state
- `set_flow(index, flow_ul_hr)` - Set flow rate
- `set_pressure(index, pressure_mbar)` - Set pressure
- `set_flow_mode(index, mode_ui)` - Set control mode
- `set_flow_pi_consts(index, p, i)` - Set PI constants

**Heater:**
- `get_heater_state()` - Get heater states
- `set_heater_temp(index, temp_c)` - Set temperature
- `set_heater_pid(index, enabled)` - Enable/disable PID
- `set_heater_stir(index, enabled)` - Enable/disable stirrer

**Camera:**
- `get_camera_snapshot()` - Get JPEG snapshot
- `set_camera_resolution(...)` - Set resolution
- `set_camera_roi(x, y, w, h)` - Set ROI
- `clear_camera_roi()` - Clear ROI

**Strobe:**
- `set_strobe_enable(enabled)` - Enable/disable
- `set_strobe_hold(hold)` - Enable/disable hold mode
- `set_strobe_timing(period_ns, wait_ns)` - Set timing

**Droplet Detection:**
- `droplet_start()` - Start detection
- `droplet_stop()` - Stop detection
- `droplet_status()` - Get status
- `droplet_histogram()` - Get histogram
- `droplet_statistics()` - Get statistics

**Data Capture:**
- `capture_start(topics, channels, path)` - Start CSV capture
- `capture_stop()` - Stop capture
- `capture_status()` - Get capture status

### WoT Thing Access (Alternative)

For WoT-compliant access, you can use LabThings ThingClient:

```python
from labthings_fastapi.client import ThingClient

# Connect to FlowThing
flow = ThingClient("http://192.168.1.100:8000/flow/")

# Get state (property)
state = flow.state

# Set flow (action)
flow.set_flow(index=0, flow_ul_hr=100.0)
```

See LabThings documentation for more details on ThingClient usage.

## WebSocket Client (`RioStreamClient`)

### Thread-Safe Message Queue

The WebSocket client uses a thread-safe queue for message delivery:

```python
stream = RioStreamClient(base_url="http://localhost:8000")
stream.subscribe(["flow", "pressure"], channels={"flow": [0, 1]})

# Messages are queued in background thread
for msg in stream.iter_messages(timeout=10.0):
    print(f"{msg['topic']}: {msg['value']}")
```

### Message Format

Messages are dictionaries with:
- `topic`: "flow", "pressure", or "heater"
- `channel`: Channel index (0-3)
- `timestamp`: Unix timestamp (float)
- `value`: Sensor value (float)
- `unit`: Unit string (e.g., "ul_hr", "mbar", "celsius")

### Connection Management

The client automatically connects when `iter_messages()` is called. Close explicitly:

```python
stream.close()  # Close WebSocket connection
```

Or use context manager:
```python
with RioStreamClient() as stream:
    # Connection automatically closed on exit
    pass
```

## Jupyter Notebooks

### Tutorial Notebook (`notebooks/tutorial.ipynb`)

A step-by-step learning notebook covering:
- System health and capabilities
- Channel configuration
- Flow/pressure control
- Heater control
- Camera snapshots
- WebSocket streaming
- Data visualization
- On-demand data capture

**Best for:** Learning the API, understanding concepts, exploring features.

### Interactive Control Notebook (`notebooks/interactive_control.ipynb`)

An interactive UI with ipywidgets for practical control:
- Flow/pressure sliders with real-time updates
- Heater controls with PID/stirrer toggles
- Camera snapshot capture
- Strobe timing controls
- Emergency stop button

**Best for:** Daily use, quick adjustments, real-time monitoring.

## Configuration

Set the API base URL via environment variable:

```bash
export RIO_API_URL="http://192.168.1.100:8000"
```

Or in Python:
```python
import os
os.environ["RIO_API_URL"] = "http://192.168.1.100:8000"
```

Or pass directly:
```python
client = RioClient(base_url="http://192.168.1.100:8000")
```

## Troubleshooting

### Connection Errors

**"Failed to connect"**:
- Check that the API server is running
- Verify the IP address and port
- Check firewall/network settings
- Try `client.health()` to test connection

### Import Errors

**"No module named 'api.client'"**:
- Make sure you're running from the repo root or have `software/` in your Python path
- In Jupyter, the notebook should handle path setup automatically
- If not, add manually: `sys.path.insert(0, '/path/to/rio-controller/software')`

### WebSocket Issues

**No messages received**:
- Check that you've called `subscribe()` before `iter_messages()`
- Verify the API server supports WebSocket (check `/api/streams/aggregate`)
- Check network connectivity
- Look for errors in the notebook output

## Examples

See the Jupyter notebooks in `notebooks/` for complete examples:
- `tutorial.ipynb`: Comprehensive tutorial with explanations
- `interactive_control.ipynb`: Practical control interface

## API Documentation

For complete API documentation, see:
- API server README: `../README.md`
- OpenAPI/Swagger docs: `http://<API_BASE_URL>/docs` (when server is running)

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-01-XX
- Maintenance: If you change the client API, methods, or behavior, update this document.

