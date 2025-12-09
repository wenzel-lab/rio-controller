# Software Structure

## Directory Organization

```
software/
├── main.py                 # Application entry point
├── config.py               # Configuration constants (system-wide)
├── rio-webapp/             # Web application components
│   ├── controllers/        # MVC controllers (web layer)
│   │   ├── camera_controller.py
│   │   ├── flow_controller.py
│   │   ├── heater_controller.py
│   │   └── view_model.py
│   ├── templates/          # HTML templates
│   │   ├── index.html
│   │   ├── camera_pi.html
│   │   └── camera_none.html
│   └── static/             # JavaScript, CSS
│       └── roi_selector.js
│
├── drivers/                # Low-level device drivers
│   ├── spi_handler.py      # SPI and GPIO communication
│   ├── flow.py             # Low-level flow controller driver
│   ├── heater.py           # Low-level heater driver
│   ├── strobe.py           # Low-level strobe driver
│   └── camera/             # Camera abstraction layer
│       ├── camera_base.py
│       ├── pi_camera_legacy.py
│       └── pi_camera_v2.py
│
├── controllers/            # High-level device controllers
│   ├── flow_web.py        # Flow web interface
│   ├── heater_web.py       # Heater web interface
│   ├── camera.py           # Camera controller
│   └── strobe_cam.py       # Strobe-camera integration
│
├── simulation/             # Simulation layer
│   ├── camera_simulated.py
│   ├── flow_simulated.py
│   ├── strobe_simulated.py
│   └── spi_simulated.py
│
└── droplet-detection/      # Droplet detection (future)
```

## Import Paths

### From `software/main.py`:
```python
from drivers.spi_handler import spi_init, PORT_*
from controllers.heater_web import heater_web
from controllers.camera import Camera
from controllers.flow_web import FlowWeb
# Webapp controllers imported from rio-webapp/controllers/
from camera_controller import CameraController
from flow_controller import FlowController
from heater_controller import HeaterController
from view_model import ViewModel
```

### From device controllers:
```python
from drivers.spi_handler import spi_init, PORT_*, GPIO, spi, spi_select_device, etc.
from drivers.flow import PiFlow
from drivers.heater import PiHolder
from drivers.strobe import PiStrobe
```

### From simulation:
```python
from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO
from simulation.camera_simulated import SimulatedCamera
```

## Rationale

1. **Clear separation**: Drivers handle low-level hardware, controllers handle high-level logic
2. **No "src" folder**: Direct access to modules
3. **Logical grouping**: Related functionality grouped together
4. **Scalable**: Easy to add new modules

