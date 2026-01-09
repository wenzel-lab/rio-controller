"""
Rio API server (skeleton + controller wiring).

- Provides minimal /api/system/health and /api/system/capabilities endpoints.
- Instantiates controllers so capabilities can reflect reality (simulation or hardware).
- Designed to run alongside the existing Flask UI, but only one process should
  own hardware. The API can be the hardware-owning process; the UI can call it
  via adapters (future step).
"""

import logging
import os
from threading import Event

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.schemas import HealthResponse, CapabilitiesResponse

# Path/bootstrap and controller imports (align with software/main.py)
from path_bootstrap import bootstrap_runtime

bootstrap_runtime()

from drivers.spi_handler import (  # noqa: E402
    spi_init,
    PORT_HEATER1,
    PORT_HEATER2,
    PORT_HEATER3,
    PORT_HEATER4,
    PORT_FLOW,
)
from controllers.heater_web import heater_web  # noqa: E402
from controllers.flow_web import FlowWeb  # noqa: E402
from controllers.camera import Camera  # noqa: E402


logger = logging.getLogger("api")


class _DummySocketIO:
    """Minimal stub to satisfy controllers that expect socketio."""

    def emit(self, *args, **kwargs):
        logger.debug("DummySocketIO emit: args=%s kwargs=%s", args, kwargs)

    def on(self, event, handler=None):
        logger.debug("DummySocketIO on: event=%s handler=%s", event, handler)
        return handler


def _init_controllers():
    """Initialize controllers (simulation-safe) and return capability flags + instances."""
    cap = {
        "flow": False,
        "pressure": False,
        "heater": False,
        "strobe": False,
        "camera": False,
        "droplet": False,
        "pump": False,
    }
    controllers = {}

    # SPI init
    spi_init(0, 2, 30000)

    exit_event = Event()
    socketio_stub = _DummySocketIO()

    try:
        heaters = [
            heater_web(1, PORT_HEATER1),
            heater_web(2, PORT_HEATER2),
            heater_web(3, PORT_HEATER3),
            heater_web(4, PORT_HEATER4),
        ]
        controllers["heaters"] = heaters
        cap["heater"] = True
    except Exception as e:
        logger.warning("Heater init failed: %s", e)

    try:
        flow = FlowWeb(PORT_FLOW)
        controllers["flow"] = flow
        cap["flow"] = True
        cap["pressure"] = True  # same hardware/module
    except Exception as e:
        logger.warning("Flow init failed: %s", e)

    try:
        cam = Camera(exit_event, socketio_stub)
        controllers["camera"] = cam
        cap["camera"] = True
        cap["strobe"] = True  # strobe is integrated via Camera/PiStrobeCam
    except Exception as e:
        logger.warning("Camera init failed: %s", e)
        cam = None

    # Droplet is optional; require camera
    if cam is not None and os.getenv("RIO_DROPLET_ANALYSIS_ENABLED", "true").lower() == "true":
        try:
            from controllers.droplet_detector_controller import DropletDetectorController

            droplet_ctrl = DropletDetectorController(cam, cam.strobe_cam)
            controllers["droplet"] = droplet_ctrl
            cap["droplet"] = True
            # connect camera to droplet for frame feeding
            cam.droplet_controller = droplet_ctrl
        except Exception as e:
            logger.warning("Droplet init failed: %s", e)

    return cap, controllers


# Initialize controllers once at import time (simple singleton style)
CAPABILITIES, CONTROLLERS = _init_controllers()


def create_app() -> FastAPI:
    app = FastAPI(title="Rio API", version="0.2.0 (controllers wired)")

    if settings.cors_allow_all:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/system/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", simulation=settings.simulation)

    @app.get("/api/system/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        notes = {"warning": "Controllers are instantiated; API methods not yet exposed."}
        return CapabilitiesResponse(modules=CAPABILITIES, simulation=settings.simulation, notes=notes)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


