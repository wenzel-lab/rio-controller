"""
Rio API server with LabThings/WoT integration.

- Uses LabThings ThingServer to expose controllers as WoT-compliant Things
- Maintains custom endpoints for system/config/streams/data
- All Things are accessible under /api/ prefix for backward compatibility
"""

import logging
import os
from threading import Event
from typing import Any, cast

import uvicorn
import yaml
from fastapi import FastAPI
import labthings_fastapi as lt
from labthings_fastapi import server as lt_server

from api.config import settings
from api.schemas import (
    HealthResponse,
    CapabilitiesResponse,
    ChannelConfig,
    ChannelConfigResponse,
    CaptureStartRequest,
    CaptureStatusResponse,
)
from api.streams import Aggregator
from api.things import FlowThing, HeaterThing, CameraThing, DropletThing, PumpThing

# Path/bootstrap and controller imports (align with software/main.py)
from path_bootstrap import bootstrap_runtime

bootstrap_runtime()

from config import (  # noqa: E402
    load_runtime_config,
    resolve_default_backend,
    resolve_module_backend,
)

_runtime_config = load_runtime_config()
_default_backend = resolve_default_backend(_runtime_config)
if "RIO_SIMULATION" not in os.environ:
    os.environ["RIO_SIMULATION"] = "true" if _default_backend == "simulation" else "false"
_pump_backend = resolve_module_backend("syringe_pump", _runtime_config)

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
from controllers.syringe_pump_controller import SyringePumpController  # noqa: E402

logger = logging.getLogger("api")


class _DummySocketIO:
    """Minimal stub to satisfy controllers that expect socketio."""

    def emit(self, *args, **kwargs):
        logger.debug("DummySocketIO emit: args=%s kwargs=%s", args, kwargs)

    def on(self, event, handler=None):
        logger.debug("DummySocketIO on: event=%s handler=%s", event, handler)
        return handler


def _init_controllers() -> tuple[dict[str, bool], dict[str, Any]]:
    """Initialize controllers (simulation-safe) and return capability flags + instances."""
    cap: dict[str, bool] = {
        "flow": False,
        "pressure": False,
        "heater": False,
        "strobe": False,
        "camera": False,
        "droplet": False,
        "pump": False,
    }
    controllers: dict[str, Any] = {}

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

    # Pump controller (optional)
    if os.getenv("RIO_PUMP_ENABLED", "false").lower() == "true":
        try:
            pump = SyringePumpController(simulation=_pump_backend == "simulation")
            controllers["pump"] = pump
            cap["pump"] = True
        except Exception as e:
            logger.warning("Pump init failed: %s", e)

    return cap, controllers


# Initialize controllers once at import time (simple singleton style)
CAPABILITIES, CONTROLLERS = _init_controllers()

# Load channel metadata from main config file (single user-facing file)
CONFIG_FILE_PATH = os.getenv("RIO_CONFIG_FILE", "rio-config.yaml")


def _load_channels_from_yaml() -> dict[str, dict[str, dict[str, Any]]]:
    """Load channel metadata from YAML config."""
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        return data.get("channels", {}) or {}
    except Exception as e:
        logger.warning("Failed to load channel config from %s: %s", CONFIG_FILE_PATH, e)
        return {}


def _default_channel_map() -> dict[str, dict[str, dict[str, Any]]]:
    """Create default channel config."""

    def _make(n: int):
        return {
            str(i): {"enabled": True, "name": "", "liquid_type": "", "calibration_factor": 1.0}
            for i in range(n)
        }

    return {
        "flow": _make(4),
        "pressure": _make(4),
        "heater": _make(4),
    }


CHANNEL_CONFIG: dict[str, dict[str, dict[str, Any]]] = _default_channel_map()
_yaml_channels = _load_channels_from_yaml()
for topic, entries in _yaml_channels.items():
    if topic not in CHANNEL_CONFIG:
        CHANNEL_CONFIG[topic] = {}
    for k, v in entries.items():
        if k not in CHANNEL_CONFIG[topic]:
            CHANNEL_CONFIG[topic][k] = {
                "enabled": True,
                "name": "",
                "liquid_type": "",
                "calibration_factor": 1.0,
            }
        for field in ("enabled", "name", "liquid_type", "calibration_factor"):
            if field in v and v[field] is not None:
                CHANNEL_CONFIG[topic][k][field] = v[field]

AGGREGATOR = Aggregator(
    flow=CONTROLLERS.get("flow"),
    heaters=CONTROLLERS.get("heaters"),
    channel_config=CHANNEL_CONFIG,
)


def create_app() -> FastAPI:
    """Create FastAPI app with LabThings ThingServer integration."""
    try:
        from labthings_fastapi.server.config_model import ThingConfig
    except ModuleNotFoundError:
        ThingConfig = None

    if ThingConfig is None:
        thing_server = lt_server.ThingServer(settings_folder=None)

        def add_thing(path: str, cls, args) -> None:
            thing_server.add_thing(cls(*args), f"/{path}")

        if CONTROLLERS.get("flow"):
            add_thing("flow", FlowThing, [CONTROLLERS["flow"]])
        if CONTROLLERS.get("heaters"):
            add_thing("heater", HeaterThing, [CONTROLLERS["heaters"]])
        if CONTROLLERS.get("camera"):
            add_thing("camera", CameraThing, [CONTROLLERS["camera"]])
        if CONTROLLERS.get("droplet"):
            add_thing("droplet", DropletThing, [CONTROLLERS["droplet"]])
        if CONTROLLERS.get("pump"):
            add_thing("pump", PumpThing, [CONTROLLERS["pump"]])
    else:
        # Create Thing configurations with controller dependencies
        # ThingServer will instantiate them with proper interfaces
        things_config: dict[str, Any] = {}

        if CONTROLLERS.get("flow"):
            things_config["flow"] = ThingConfig(
                cls=FlowThing,
                args=[CONTROLLERS["flow"]],
            )

        if CONTROLLERS.get("heaters"):
            things_config["heater"] = ThingConfig(
                cls=HeaterThing,
                args=[CONTROLLERS["heaters"]],
            )

        if CONTROLLERS.get("camera"):
            things_config["camera"] = ThingConfig(
                cls=CameraThing,
                args=[CONTROLLERS["camera"]],
            )

        if CONTROLLERS.get("droplet"):
            things_config["droplet"] = ThingConfig(
                cls=DropletThing,
                args=[CONTROLLERS["droplet"]],
            )

        if CONTROLLERS.get("pump"):
            things_config["pump"] = ThingConfig(
                cls=PumpThing,
                args=[CONTROLLERS["pump"]],
            )

        # Create ThingServer - it will create its own FastAPI app
        thing_server = lt_server.ThingServer(things_config, settings_folder=None)

    # Get ThingServer's app
    app = thing_server.app

    # Update app title
    app.title = "Rio API"
    app.version = "0.3.0 (LabThings/WoT)"

    # CORS is already set by ThingServer with allow_origins=["*"], so we're good

    # Custom endpoints (system, config, streams, data)
    # These are mounted at root level but under /api/ prefix

    @app.get("/api/system/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", simulation=settings.simulation)

    @app.get("/api/system/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        notes = {"info": "API now uses LabThings/WoT-compliant Things"}
        return CapabilitiesResponse(
            modules=CAPABILITIES, simulation=settings.simulation, notes=notes
        )

    @app.get("/api/config/channels", response_model=ChannelConfigResponse)
    def get_channels() -> ChannelConfigResponse:
        return ChannelConfigResponse(channels=ChannelConfig(**cast(dict[str, Any], CHANNEL_CONFIG)))

    @app.post("/api/config/channels", response_model=ChannelConfigResponse)
    def set_channels(config: ChannelConfig) -> ChannelConfigResponse:
        # shallow merge; keys absent are left as-is
        for topic in ("flow", "pressure", "heater"):
            incoming = getattr(config, topic)
            if incoming is None:
                continue
            if topic not in CHANNEL_CONFIG:
                CHANNEL_CONFIG[topic] = {}
            for k, v in incoming.items():
                if k not in CHANNEL_CONFIG[topic]:
                    CHANNEL_CONFIG[topic][k] = {
                        "enabled": True,
                        "name": "",
                        "liquid_type": "",
                        "calibration_factor": 1.0,
                    }
                CHANNEL_CONFIG[topic][k]["enabled"] = bool(v.enabled)
                CHANNEL_CONFIG[topic][k]["name"] = v.name or ""
                CHANNEL_CONFIG[topic][k]["liquid_type"] = v.liquid_type or ""
                if getattr(v, "calibration_factor", None) is not None:
                    CHANNEL_CONFIG[topic][k]["calibration_factor"] = float(v.calibration_factor)
        return ChannelConfigResponse(channels=ChannelConfig(**cast(dict[str, Any], CHANNEL_CONFIG)))

    @app.websocket("/api/streams/aggregate")
    async def aggregate_ws(websocket):
        await AGGREGATOR.handle_ws(websocket)

    @app.post("/api/data/capture/start", response_model=CaptureStatusResponse)
    def capture_start(req: CaptureStartRequest):
        topics = req.topics
        channels = req.channels or {}
        AGGREGATOR.start_capture(topics, channels, req.path)
        status = AGGREGATOR.capture_status()
        return CaptureStatusResponse(**status)

    @app.post("/api/data/capture/stop", response_model=CaptureStatusResponse)
    def capture_stop():
        AGGREGATOR.stop_capture()
        status = AGGREGATOR.capture_status()
        return CaptureStatusResponse(**status)

    @app.get("/api/data/capture/status", response_model=CaptureStatusResponse)
    def capture_status():
        status = AGGREGATOR.capture_status()
        return CaptureStatusResponse(**status)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
