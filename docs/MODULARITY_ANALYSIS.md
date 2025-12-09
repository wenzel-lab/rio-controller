# Software Modularity Analysis

## Current Architecture: MVC+S (Model-View-Controller-Simulation)

The software follows a layered architecture with clear separation of concerns:

### Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                    │
│  (rio-webapp/templates/, rio-webapp/static/)             │
│  - HTML Templates (View)                                 │
│  - JavaScript (Client-side logic)                        │
│  - CSS (Styling)                                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    WEB CONTROLLER LAYER                  │
│  (rio-webapp/controllers/)                               │
│  - CameraController: WebSocket handlers for camera      │
│  - FlowController: WebSocket handlers for flow            │
│  - HeaterController: WebSocket handlers for heaters      │
│  - ViewModel: Data formatting for templates              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    MODEL LAYER                           │
│  (controllers/ - should be renamed to models/)           │
│  - Camera: Camera device management                      │
│  - FlowWeb: Flow control business logic                  │
│  - heater_web: Heater control business logic             │
│  - PiStrobeCam: Strobe-camera integration                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    DRIVER LAYER                          │
│  (drivers/)                                              │
│  - spi_handler: SPI/GPIO communication                  │
│  - flow: Low-level flow PIC communication               │
│  - heater: Low-level heater PIC communication           │
│  - strobe: Low-level strobe PIC communication            │
│  - camera/: Camera abstraction (BaseCamera, PiCamera*)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    SIMULATION LAYER                      │
│  (simulation/) - Drop-in replacement for drivers        │
│  - camera_simulated: Simulated camera                    │
│  - flow_simulated: Simulated flow controller            │
│  - strobe_simulated: Simulated strobe controller        │
│  - spi_simulated: Simulated SPI/GPIO                    │
└─────────────────────────────────────────────────────────┘
```

## Functional Modules

### 1. **Hardware Communication (Driver Layer)**
**Location**: `drivers/`

**Responsibilities**:
- Direct hardware communication via SPI/GPIO
- PIC microcontroller protocol implementation
- Camera abstraction (32-bit vs 64-bit compatibility)
- Low-level device control

**Modules**:
- `spi_handler.py`: SPI bus management, GPIO control, device selection
- `flow.py`: Flow controller PIC communication (4 channels)
- `heater.py`: Heater PIC communication (4 heaters)
- `strobe.py`: Strobe PIC communication
- `camera/`: Camera abstraction layer
  - `camera_base.py`: Abstract base class
  - `pi_camera_legacy.py`: 32-bit Pi camera (picamera)
  - `pi_camera_v2.py`: 64-bit Pi camera (picamera2)

**Modularity**: ✅ **Excellent**
- Each driver is independent
- Clear interfaces (SPI packet protocol)
- No cross-dependencies between drivers
- Simulation support via conditional imports

---

### 2. **Device Controllers (Model Layer in MVC, but "Controller" in Hardware Context)**
**Location**: `controllers/`

**Responsibilities**:
- High-level device control logic
- State management
- Business rules (control mode mapping, validation)
- Integration between multiple drivers (e.g., camera + strobe)

**Terminology Note**: In hardware control systems (like SQUID microscope software), "controller" refers to the business logic layer that controls devices. This is equivalent to "Model" in traditional MVC terminology, but "controller" is more appropriate in embedded/hardware contexts.

**Modules**:
- `camera.py`: Camera management, frame capture, ROI handling
- `flow_web.py`: Flow control with UI mode mapping
- `heater_web.py`: Heater control with PID management
- `strobe_cam.py`: Camera-strobe synchronization

**Modularity**: ⚠️ **Good, but needs improvement**
- ✅ Each controller is independent
- ✅ Clear separation from drivers
- ⚠️ `camera.py` mixes device control with WebSocket handling
- ✅ Naming is appropriate for hardware control context

---

### 3. **Web Controllers (Controller Layer)**
**Location**: `rio-webapp/controllers/`

**Responsibilities**:
- WebSocket event handling
- Request validation
- Coordination between Models and Views
- No direct hardware access

**Modules**:
- `camera_controller.py`: Camera WebSocket events
- `flow_controller.py`: Flow control WebSocket events
- `heater_controller.py`: Heater control WebSocket events
- `view_model.py`: Data formatting for templates

**Modularity**: ✅ **Excellent**
- Each controller handles one device type
- No cross-dependencies
- Clear separation from Models
- ViewModel is stateless (static methods)

---

### 4. **Presentation (View Layer)**
**Location**: `rio-webapp/templates/`, `rio-webapp/static/`

**Responsibilities**:
- HTML structure
- Client-side JavaScript
- User interface rendering
- No business logic

**Modules**:
- `templates/index.html`: Main application page
- `templates/camera_pi.html`: Camera view
- `templates/camera_none.html`: No camera placeholder
- `static/roi_selector.js`: ROI selection JavaScript

**Modularity**: ✅ **Excellent**
- Pure presentation
- No server-side logic
- Clear separation from controllers

---

### 5. **Simulation Layer**
**Location**: `simulation/`

**Responsibilities**:
- Drop-in replacement for drivers
- Mock hardware responses
- Testing without physical hardware
- Same API as real drivers

**Modules**:
- `camera_simulated.py`: Simulated camera with configurable FPS
- `flow_simulated.py`: Simulated flow controller
- `strobe_simulated.py`: Simulated strobe controller
- `spi_simulated.py`: Simulated SPI/GPIO

**Modularity**: ✅ **Excellent**
- Perfect API matching with real drivers
- Conditional import in `spi_handler.py`
- No changes needed in Models when switching

---

### 6. **Application Entry Point**
**Location**: `main.py`

**Responsibilities**:
- Flask app initialization
- Route definitions
- Background tasks
- Dependency injection

**Modularity**: ⚠️ **Good, but could be improved**
- ✅ Clear initialization sequence
- ⚠️ Route handlers mixed with initialization
- ⚠️ Could separate routes into dedicated module

---

## Modularity Improvements Needed

### 1. ~~**Rename `controllers/` to `models/`**~~ ✅ **DECISION: Keep `controllers/`**
**Rationale**: In hardware control systems, "controller" is the standard term for device control logic (e.g., SQUID microscope software). This is equivalent to "Model" in MVC, but "controller" is more appropriate and self-explanatory in embedded contexts.
**Action**: ✅ Keep `controllers/` folder name, document terminology clearly

### 2. **Separate Camera WebSocket Handling**
**Issue**: `Camera` class in `controllers/camera.py` has WebSocket methods mixed with device control
**Impact**: Medium (violates single responsibility)
**Action**: Move WebSocket handling to `CameraController`, keep Camera as pure Model

### 3. **Extract Routes Module**
**Issue**: Route handlers in `main.py` mix with initialization
**Impact**: Low (works but could be cleaner)
**Action**: Create `rio-webapp/routes.py` for Flask route definitions

### 4. **Clarify Naming Conventions**
**Issue**: `flow_web.py` and `heater_web.py` have "web" suffix but are Models
**Impact**: Low (confusing but functional)
**Action**: Consider renaming to `flow_model.py` and `heater_model.py` (or keep as is if "web" means "web-interface wrapper")

---

## Current Modularity Strengths

1. ✅ **Clear Layer Separation**: MVC+S layers are well-defined
2. ✅ **Driver Abstraction**: All hardware access through drivers
3. ✅ **Simulation Support**: Complete simulation layer with same API
4. ✅ **Independent Modules**: Each module has single responsibility
5. ✅ **No Circular Dependencies**: Clean import hierarchy
6. ✅ **Configuration Centralization**: `config.py` for all constants
7. ✅ **Test Structure**: Dedicated `tests/` folder with organized test files

---

## Recommendations

### High Priority
1. **Rename `controllers/` → `models/`** for clarity
2. **Separate Camera WebSocket handling** from Camera device control

### Medium Priority
3. **Extract routes** from `main.py` to `rio-webapp/routes.py`
4. **Add `__init__.py` files** with clear module documentation

### Low Priority
5. Consider renaming `*_web.py` files to `*_model.py` for consistency
6. Add type hints to all public methods
7. Create module-level docstrings explaining each module's purpose

---

## Module Dependency Graph

```
main.py
  ├── controllers/ (Device Controllers - equivalent to Models in MVC)
  │   ├── camera.py → drivers/camera/, drivers/strobe.py
  │   ├── flow_web.py → drivers/flow.py
  │   ├── heater_web.py → drivers/heater.py
  │   └── strobe_cam.py → drivers/strobe.py, drivers/camera/
  │
  ├── rio-webapp/controllers/ (Web Controllers - HTTP/WebSocket handlers)
  │   ├── camera_controller.py → controllers/camera.py
  │   ├── flow_controller.py → controllers/flow_web.py
  │   ├── heater_controller.py → controllers/heater_web.py
  │   └── view_model.py → controllers/flow_web.py, controllers/camera.py
  │
  ├── drivers/
  │   ├── spi_handler.py → simulation/spi_simulated.py (conditional)
  │   ├── flow.py → drivers/spi_handler.py
  │   ├── heater.py → drivers/spi_handler.py
  │   ├── strobe.py → drivers/spi_handler.py
  │   └── camera/ → simulation/camera_simulated.py (conditional)
  │
  └── simulation/ (drop-in replacements)
      ├── spi_simulated.py
      ├── flow_simulated.py
      ├── heater_simulated.py (via flow_simulated)
      ├── strobe_simulated.py
      └── camera_simulated.py
```

**Key Points**:
- Models depend on Drivers (one-way)
- Web Controllers depend on Models (one-way)
- Drivers conditionally use Simulation (via environment variable)
- No circular dependencies
- Clear separation of concerns

