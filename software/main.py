"""
Main Flask application entry point for Rio microfluidics controller.

This module follows MVC+S architecture (Model-View-Controller-Simulation):
- Device Controllers (controllers/): Business logic for device control
- Web Controllers (rio-webapp/controllers/): HTTP/WebSocket handlers
- Views (rio-webapp/templates/): HTML templates and static files
- Drivers (drivers/): Low-level hardware communication
- Simulation (simulation/): Hardware replacement for testing

Architecture layers:
1. Routes (rio-webapp/routes.py): HTTP route definitions
2. Web Controllers: WebSocket event handlers
3. Device Controllers: Business logic and state management
4. Drivers: Hardware communication abstraction
5. Simulation: Drop-in hardware replacement (when RIO_SIMULATION=true)

See docs/ARCHITECTURE_TERMINOLOGY.md for terminology explanation.

Usage:
    python main.py [PORT]

    Or set RIO_PORT environment variable for port number.
"""

import os
import sys
import logging
from threading import Event
from flask import Flask
from flask_socketio import SocketIO
import eventlet

# Add current directory to path for imports (we're now at software/ level)
software_dir = os.path.dirname(os.path.abspath(__file__))
if software_dir not in sys.path:
    sys.path.insert(0, software_dir)

from drivers.spi_handler import (  # noqa: E402
    spi_init,
    PORT_HEATER1,
    PORT_HEATER2,
    PORT_HEATER3,
    PORT_HEATER4,
    PORT_FLOW,
)
from controllers.heater_web import heater_web  # noqa: E402
from controllers.camera import Camera  # noqa: E402
from controllers.flow_web import FlowWeb  # noqa: E402

# Import webapp controllers from rio-webapp/controllers
# Note: There's a naming conflict - we have both:
#   - software/controllers/ (device controllers: flow_web, heater_web, camera, strobe_cam)
#   - software/rio-webapp/controllers/ (web controllers: camera_controller, flow_controller, etc.)
# Solution: Import directly from the files to avoid package name conflict
rio_webapp_controllers_dir = os.path.join(software_dir, "rio-webapp", "controllers")
if rio_webapp_controllers_dir not in sys.path:
    sys.path.insert(0, rio_webapp_controllers_dir)

# Import directly from controller files
from camera_controller import CameraController  # noqa: E402
from flow_controller import FlowController  # noqa: E402
from heater_controller import HeaterController  # noqa: E402
from view_model import ViewModel  # noqa: E402

# Import routes module (from rio-webapp directory)
rio_webapp_dir = os.path.join(software_dir, "rio-webapp")
if rio_webapp_dir not in sys.path:
    sys.path.insert(0, rio_webapp_dir)
from routes import register_routes, create_background_update_task  # noqa: E402

# Configure eventlet monkey patching
eventlet.monkey_patch(os=True, select=True, socket=True, thread=False, time=True, psycopg=True)

# Configure logging
# Use configurable log level (default: WARNING for production, can override with RIO_LOG_LEVEL)
try:
    from config import RIO_LOG_LEVEL
    log_level = getattr(logging, RIO_LOG_LEVEL, logging.WARNING)
except (ImportError, AttributeError):
    # Fallback to WARNING if config not available or invalid level
    log_level = logging.WARNING

logging.basicConfig(
    level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global state
exit_event = Event()
debug_data = {"update_count": 0}

# Initialize hardware communication
logger.info("Initializing SPI communication...")
spi_init(0, 2, 30000)

# Create Flask app and SocketIO first (needed for Camera initialization)
app = Flask(
    __name__,
    template_folder=os.path.join(software_dir, "rio-webapp", "templates"),
    static_folder=os.path.join(software_dir, "rio-webapp", "static"),
    static_url_path="/static",
)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# Initialize hardware models (after SPI init and Flask/SocketIO setup)
logger.info("Initializing hardware models...")
heater1 = heater_web(1, PORT_HEATER1)
heater2 = heater_web(2, PORT_HEATER2)
heater3 = heater_web(3, PORT_HEATER3)
heater4 = heater_web(4, PORT_HEATER4)
heaters = [heater1, heater2, heater3, heater4]

flow = FlowWeb(PORT_FLOW)

# Camera needs exit_event and socketio
cam = Camera(exit_event, socketio)

# Initialize droplet detector controller (after camera is created)
# Check if module is enabled (default: True for backward compatibility)
droplet_controller = None
droplet_web_controller = None

# Check module enable flag (can be set via environment variable)
# Format: RIO_DROPLET_ANALYSIS_ENABLED=true or false
droplet_analysis_enabled = os.getenv("RIO_DROPLET_ANALYSIS_ENABLED", "true").lower() == "true"

if droplet_analysis_enabled:
    try:
        from controllers.droplet_detector_controller import DropletDetectorController

        droplet_controller = DropletDetectorController(cam, cam.strobe_cam)
        # Set droplet controller reference in camera for frame feeding
        cam.droplet_controller = droplet_controller
        logger.info("Droplet detector controller initialized")
    except ImportError as e:
        logger.warning(f"Droplet detection not available (missing dependencies): {e}")
    except Exception as e:
        logger.warning(f"Failed to initialize droplet detector: {e}")
else:
    logger.info("Droplet analysis module disabled (RIO_DROPLET_ANALYSIS_ENABLED=false)")

# Initialize controllers
logger.info("Initializing controllers...")
camera_controller = CameraController(cam, socketio)
flow_controller = FlowController(flow, socketio)
heater_controller = HeaterController(heaters, socketio)

# Initialize droplet web controller if available
if droplet_controller is not None:
    try:
        # Import from rio-webapp/controllers
        rio_webapp_controllers_dir = os.path.join(software_dir, "rio-webapp", "controllers")
        if rio_webapp_controllers_dir not in sys.path:
            sys.path.insert(0, rio_webapp_controllers_dir)
        from droplet_web_controller import DropletWebController

        droplet_web_controller = DropletWebController(droplet_controller, socketio)
        logger.info("Droplet web controller initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize droplet web controller: {e}")

view_model = ViewModel(
    flow, cam
)  # ViewModel now accepts flow and camera for backward compatibility

# Note: All web controllers register their WebSocket handlers automatically in __init__()
# No need to call register_handlers() separately

# Register Flask routes and WebSocket handlers
register_routes(app, socketio, view_model, heaters, flow, cam, debug_data, droplet_controller)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rio Microfluidics Controller Web App")
    parser.add_argument(
        "port",
        type=int,
        nargs="?",
        default=int(os.getenv("RIO_PORT", "5000")),
        help="Port number to run the web app on",
    )
    args = parser.parse_args()

    port = args.port

    logger.info(f"Starting Rio microfluidics controller on port {port}...")
    logger.info(f"If port is in use, kill the process with: lsof -ti:{port} | xargs kill -9")
    logger.info("Or use a different port: python main.py <PORT_NUMBER>")

    # Start background update thread
    background_task = create_background_update_task(
        socketio, view_model, heaters, flow, cam, debug_data, droplet_web_controller
    )
    socketio.start_background_task(background_task)

    try:
        socketio.run(app, host="0.0.0.0", port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        exit_event.set()
    finally:
        logger.info("Server stopped")
