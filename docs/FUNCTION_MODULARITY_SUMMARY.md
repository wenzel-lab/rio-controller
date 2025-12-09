# Function Modularity Summary

This document lists all functional modules in the Rio microfluidics controller software and explains how modularity is maintained.

## Module Categories

### 1. Hardware Communication (Driver Layer)
**Location**: `software/drivers/`

#### `spi_handler.py`
**Purpose**: SPI bus and GPIO communication abstraction
**Functions**:
- `spi_init(bus, mode, speed_hz)`: Initialize SPI bus
- `spi_close()`: Close SPI bus
- `spi_select_device(device)`: Select SPI device via GPIO
- `spi_deselect_current()`: Deselect current SPI device
- `spi_lock()`: Acquire SPI lock
- `spi_release()`: Release SPI lock
- `pi_wait_s(delay_s)`: Platform-independent delay

**Modularity**: ✅
- Conditional import: Uses `simulation/spi_simulated.py` when `RIO_SIMULATION=true`
- No dependencies on other drivers
- Pure hardware abstraction layer

---

#### `flow.py` - `PiFlow` class
**Purpose**: Low-level flow controller PIC communication
**Key Methods**:
- `packet_query(packet_type, data)`: SPI packet communication
- `set_pressure(channel, pressure_mbar)`: Set target pressure
- `get_pressure(channel)`: Get current pressure
- `set_flow(channel, flow_ul_hr)`: Set target flow rate
- `get_flow(channel)`: Get current flow rate
- `set_control_mode(channel, mode)`: Set control mode
- `get_control_mode(channel)`: Get control mode
- `set_flow_pi_consts(channel, consts)`: Set PI control constants
- `get_flow_pi_consts(channel)`: Get PI control constants

**Modularity**: ✅
- Depends only on `spi_handler`
- No dependencies on other device drivers
- Clean SPI protocol implementation

---

#### `heater.py` - `PiHolder` class
**Purpose**: Low-level heater PIC communication
**Key Methods**:
- `packet_query(packet_type, data)`: SPI packet communication
- `set_temp(channel, temp_c)`: Set target temperature
- `get_temp(channel)`: Get current temperature
- `set_pid_running(channel, enabled)`: Enable/disable PID
- `set_heat_power_limit_pc(channel, limit)`: Set power limit
- `set_autotune(channel, enabled)`: Enable/disable autotune
- `set_stir_running(channel, enabled)`: Enable/disable stirring

**Modularity**: ✅
- Depends only on `spi_handler`
- No dependencies on other device drivers
- Clean SPI protocol implementation

---

#### `strobe.py` - `PiStrobe` class
**Purpose**: Low-level strobe PIC communication
**Key Methods**:
- `packet_query(packet_type, data)`: SPI packet communication
- `set_timing(wait_ns, period_ns)`: Set strobe timing
- `set_enable(enabled)`: Enable/disable strobe
- `set_hold(hold_ns)`: Set strobe hold time
- `get_cam_read_time()`: Get camera read time
- `set_trigger_mode(enabled)`: Set hardware trigger mode

**Modularity**: ✅
- Depends only on `spi_handler`
- No dependencies on other device drivers
- Clean SPI protocol implementation

---

#### `camera/` - Camera Abstraction Layer
**Purpose**: Camera hardware abstraction (32-bit vs 64-bit compatibility)

**`camera_base.py` - `BaseCamera` abstract class**
- `start()`: Start camera
- `stop()`: Stop camera
- `get_frame()`: Get current frame
- `set_config(config)`: Set camera configuration
- `set_roi(roi)`: Set region of interest
- `set_frame_callback(callback)`: Set frame callback

**`pi_camera_legacy.py` - `PiCameraLegacy` class**
- Implements `BaseCamera` for 32-bit Pi (picamera library)

**`pi_camera_v2.py` - `PiCameraV2` class**
- Implements `BaseCamera` for 64-bit Pi (picamera2 library)

**`create_camera()` function**
- Factory function that auto-detects 32-bit vs 64-bit
- Returns appropriate camera implementation

**Modularity**: ✅
- Clean abstraction via base class
- No dependencies on other drivers
- Conditional import for simulation

---

### 2. Device Controllers (Model Layer)
**Location**: `software/controllers/`

#### `camera.py` - `Camera` class
**Purpose**: High-level camera management with strobe integration
**Key Methods**:
- `__init__(exit_event, socketio)`: Initialize camera controller
- `initialize()`: Start camera thread
- `get_frame()`: Get current frame (JPEG bytes)
- `set_timing()`: Set strobe timing
- `on_cam(data)`: Handle camera WebSocket commands
- `on_strobe(data)`: Handle strobe WebSocket commands
- `on_roi(data)`: Handle ROI WebSocket commands
- `update_strobe_data()`: Update strobe state
- `_register_websocket_handlers()`: Register WebSocket handlers

**Modularity**: ⚠️ **Good, but mixes concerns**
- ✅ Depends on `drivers/camera/` and `controllers/strobe_cam`
- ⚠️ Contains WebSocket handling (should be in web controller)
- ✅ Clear separation from low-level drivers

---

#### `flow_web.py` - `FlowWeb` class
**Purpose**: High-level flow control with UI mode mapping
**Key Methods**:
- `__init__(port)`: Initialize flow controller
- `update()`: Update flow state from hardware
- `set_pressure(channel, pressure_mbar)`: Set target pressure
- `set_flow(channel, flow_ul_hr)`: Set target flow rate
- `set_control_mode(channel, mode)`: Set control mode (with UI mapping)
- `set_flow_pi_consts(channel, consts)`: Set PI constants
- Properties: `status_text`, `pressure_mbar_text`, `flow_ul_hr_text`, etc.

**Modularity**: ✅
- Depends only on `drivers/flow`
- No WebSocket handling (handled by web controller)
- Clean business logic layer

---

#### `heater_web.py` - `heater_web` class
**Purpose**: High-level heater control with PID management
**Key Methods**:
- `__init__(channel, port)`: Initialize heater controller
- `update()`: Update heater state from hardware
- `set_temp(temp_c)`: Set target temperature
- `set_pid_running(enabled)`: Enable/disable PID
- `set_heat_power_limit_pc(limit)`: Set power limit
- `set_autotune(enabled)`: Enable/disable autotune
- `set_stir_running(enabled)`: Enable/disable stirring
- Properties: `status_text`, `temp_text`, `pid_enabled`, etc.

**Modularity**: ✅
- Depends only on `drivers/heater`
- No WebSocket handling (handled by web controller)
- Clean business logic layer

---

#### `strobe_cam.py` - `PiStrobeCam` class
**Purpose**: Camera-strobe synchronization integration
**Key Methods**:
- `__init__(port, reply_pause_s, trigger_gpio_pin)`: Initialize
- `set_timing(pre_padding_ns, strobe_period_ns, post_padding_ns)`: Set timing
- `frame_callback_trigger()`: GPIO trigger on frame capture
- `set_enable(enabled)`: Enable/disable strobe

**Modularity**: ✅
- Depends on `drivers/strobe` and `drivers/camera/`
- Integrates two drivers cleanly
- No WebSocket handling

---

### 3. Web Controllers (Controller Layer)
**Location**: `software/rio-webapp/controllers/`

#### `camera_controller.py` - `CameraController` class
**Purpose**: WebSocket handlers for camera operations
**Key Methods**:
- `__init__(camera, socketio)`: Initialize controller
- `handle_camera_select(data)`: Handle camera selection command
- `_register_handlers()`: Register WebSocket event handlers

**Modularity**: ✅
- Depends on `controllers/camera` (device controller)
- Pure web layer - no hardware access
- Single responsibility: WebSocket handling

---

#### `flow_controller.py` - `FlowController` class
**Purpose**: WebSocket handlers for flow control
**Key Methods**:
- `__init__(flow, socketio)`: Initialize controller
- `handle_flow_command(data)`: Handle flow control commands
- `_register_handlers()`: Register WebSocket event handlers

**Modularity**: ✅
- Depends on `controllers/flow_web` (device controller)
- Pure web layer - no hardware access
- Single responsibility: WebSocket handling

---

#### `heater_controller.py` - `HeaterController` class
**Purpose**: WebSocket handlers for heater control
**Key Methods**:
- `__init__(heaters, socketio)`: Initialize controller
- `handle_heater_command(data)`: Handle heater control commands
- `_register_handlers()`: Register WebSocket event handlers

**Modularity**: ✅
- Depends on `controllers/heater_web` (device controller)
- Pure web layer - no hardware access
- Single responsibility: WebSocket handling

---

#### `view_model.py` - `ViewModel` class
**Purpose**: Data formatting for template rendering
**Key Methods** (all static):
- `format_heater_data(heaters)`: Format heater data for template
- `format_flow_data(flow)`: Format flow data for template
- `format_camera_data(camera)`: Format camera data for template
- `format_strobe_data(camera)`: Format strobe data for template
- `format_debug_data(update_count)`: Format debug data

**Modularity**: ✅
- Stateless (all static methods)
- Pure data transformation
- No side effects
- Depends on device controllers for data access

---

### 4. Routes (Web Layer)
**Location**: `software/rio-webapp/routes.py`

#### `register_routes(app, socketio, view_model, heaters, flow, cam, debug_data)`
**Purpose**: Register all Flask HTTP routes and WebSocket handlers
**Routes**:
- `GET /`: Main page with device status
- `GET /video`: MJPEG video stream
- `WebSocket connect`: Client connection handler
- `WebSocket disconnect`: Client disconnection handler

#### `create_background_update_task(socketio, view_model, heaters, flow, cam, debug_data)`
**Purpose**: Create background task for periodic data updates
**Functionality**:
- Updates device controllers every 1 second
- Formats data using ViewModel
- Emits updates to WebSocket clients

**Modularity**: ✅
- Separated from `main.py` for clarity
- Pure route definitions
- No business logic

---

### 5. Simulation Layer
**Location**: `software/simulation/`

#### `spi_simulated.py` - `SimulatedSPIHandler` class
**Purpose**: Simulated SPI/GPIO for testing
**Modularity**: ✅
- Drop-in replacement for `spi_handler`
- Same API as real hardware
- Logs all SPI transfers

#### `camera_simulated.py` - `SimulatedCamera` class
**Purpose**: Simulated camera for testing
**Modularity**: ✅
- Implements `BaseCamera` interface
- Generates synthetic frames
- Configurable FPS and patterns

#### `flow_simulated.py` - `SimulatedFlowController` class
**Purpose**: Simulated flow controller for testing
**Modularity**: ✅
- Same API as `PiFlow`
- Simulates pressure/flow values
- Supports all control modes

#### `strobe_simulated.py` - `SimulatedStrobeController` class
**Purpose**: Simulated strobe controller for testing
**Modularity**: ✅
- Same API as `PiStrobe`
- Simulates timing responses
- Supports trigger modes

---

## Modularity Principles Applied

### ✅ **Single Responsibility**
Each module has one clear purpose:
- Drivers: Hardware communication only
- Device Controllers: Business logic only
- Web Controllers: WebSocket handling only
- Routes: HTTP route definitions only
- ViewModel: Data formatting only

### ✅ **Dependency Direction**
Clear one-way dependencies:
```
Routes → Web Controllers → Device Controllers → Drivers
```

### ✅ **Abstraction Layers**
- Camera abstraction hides 32-bit vs 64-bit differences
- Simulation layer provides drop-in hardware replacement
- SPI handler abstracts platform differences

### ✅ **No Circular Dependencies**
- Each layer only depends on layers below it
- No module depends on modules at the same level
- Clear import hierarchy

### ✅ **Interface Consistency**
- All drivers follow same SPI packet protocol
- All cameras implement `BaseCamera` interface
- Simulation classes match real hardware APIs

### ✅ **Configuration Centralization**
- All constants in `config.py`
- Environment variables for mode selection
- No hardcoded values in modules

---

## Areas for Improvement

### ⚠️ **Camera WebSocket Handling**
**Issue**: `Camera` class in `controllers/camera.py` has WebSocket methods
**Impact**: Mixes device control with web layer concerns
**Recommendation**: Move WebSocket handling entirely to `CameraController`

### ✅ **Routes Extraction** (Completed)
**Action**: Extracted routes from `main.py` to `rio-webapp/routes.py`
**Benefit**: Cleaner separation, easier to test routes independently

---

## Summary

The software maintains excellent modularity through:
1. **Clear layer separation** (Driver → Device Controller → Web Controller → Routes)
2. **Single responsibility** for each module
3. **Consistent interfaces** across similar modules
4. **No circular dependencies**
5. **Abstraction layers** for hardware differences
6. **Simulation support** for testing without hardware

The architecture follows hardware control system conventions while maintaining web application best practices.

