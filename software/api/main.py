"""
Rio API server with LabThings/WoT integration.

- Uses LabThings ThingServer to expose controllers as WoT-compliant Things
- Maintains custom endpoints for system/config/streams/data
- All Things are accessible under /api/ prefix for backward compatibility
"""

import logging
import os
from threading import Event
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import labthings_fastapi as lt

from api.config import settings
from api.schemas import (
    HealthResponse,
    CapabilitiesResponse,
    ChannelConfig,
    ChannelConfigResponse,
    CaptureStartRequest,
    CaptureStatusResponse,
    FlowState,
    FlowSetPressureRequest,
    FlowSetFlowRequest,
    FlowSetModeRequest,
    FlowSetPIRequest,
    HeaterState,
    HeaterStateItem,
    HeaterSetTempRequest,
    HeaterSetPidRequest,
    HeaterSetStirRequest,
    CameraResolutionRequest,
    CameraSnapshotResolutionRequest,
    CameraROIRequest,
    StrobeEnableRequest,
    StrobeTimingRequest,
    PumpSetFlowRequest,
    PumpSetDiameterRequest,
    PumpSetDirectionRequest,
    PumpSetStateRequest,
    PumpSetUnitRequest,
    PumpSetGearboxRequest,
    PumpSetMicrostepRequest,
    PumpSetThreadrodRequest,
    PumpSetEnableRequest,
)
from api.streams import Aggregator
from api.things import FlowThing, HeaterThing, CameraThing, DropletThing, PumpThing

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
from controllers.pump_controller import PumpController  # noqa: E402
from config import (  # noqa: E402
    CMD_SET_RESOLUTION,
    CMD_SET_SNAPSHOT_RESOLUTION,
    CMD_SET,
    CMD_CLEAR,
    CMD_TIMING,
    CMD_ENABLE,
    CMD_HOLD,
)

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

    # Pump controller (optional; USB serial)
    if os.getenv("RIO_PUMP_ENABLED", "false").lower() == "true":
        try:
            pump = PumpController()
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
    from labthings_fastapi.server.config_model import ThingConfig

    # Create Thing configurations with controller dependencies
    # ThingServer will instantiate them with proper interfaces
    things_config: dict[str, ThingConfig | type[lt.Thing]] = {}

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
    thing_server = lt.ThingServer(things_config, settings_folder=None)

    # Use ThingServer's app as the base - add our custom routes to it
    # ThingServer routes are at root level (e.g., /flow/, /heater/, /docs)
    # We'll add custom routes at /api/ prefix for backward compatibility
    app = thing_server.app

    # Update app title
    app.title = "Rio API"
    app.version = "0.3.0 (LabThings/WoT)"

    # CORS is already set by ThingServer with allow_origins=["*"]
    # Note: ThingServer creates routes at root (e.g., /flow/, /heater/)
    # Custom routes are at /api/ prefix for backward compatibility

    # Custom endpoints (system, config, streams, data)
    @app.get("/api/system/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", simulation=settings.simulation)

    @app.get("/api/system/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        notes = {
            "info": "API now uses LabThings/WoT-compliant Things",
            "wot_routes": "Things available at /flow/, /heater/, /camera/, /droplet/, /pump/",
            "backward_compat": "Legacy /api/control/* routes redirect to WoT Things",
        }
        return CapabilitiesResponse(
            modules=CAPABILITIES, simulation=settings.simulation, notes=notes
        )

    # Backward compatibility: Legacy /api/control/* routes
    # These call controllers directly (same as old implementation) for compatibility
    # WoT routes are available at /flow/, /heater/, etc. for new clients

    @app.get("/api/control/flow/state", response_model=FlowState)
    def flow_state_legacy() -> FlowState:
        """Legacy endpoint - calls Flow controller directly."""
        flow: FlowWeb | None = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")

        ok_p, pressure_actuals = flow.flow.get_pressure_actual()
        if not ok_p:
            pressure_actuals = [0.0] * flow.flow.NUM_CONTROLLERS
        ok_f, flow_actuals = flow.flow.get_flow_actual()
        if not ok_f:
            flow_actuals = [0.0] * flow.flow.NUM_CONTROLLERS

        flow.get_pressure_targets()
        flow.get_flow_targets()
        flow.get_control_modes()

        from config import CONTROL_MODE_FIRMWARE_TO_UI

        return FlowState(
            pressure_targets_mbar=flow.pressure_mbar_targets,
            pressure_actuals_mbar=pressure_actuals,
            flow_targets_ul_hr=flow.flow_ul_hr_targets,
            flow_actuals_ul_hr=flow_actuals,
            control_modes_ui=[CONTROL_MODE_FIRMWARE_TO_UI.get(m, 0) for m in flow.control_modes],
            control_modes_text=flow.control_modes_text,
        )

    @app.post("/api/control/flow/set_pressure")
    def flow_set_pressure_legacy(req: FlowSetPressureRequest):
        """Legacy endpoint - calls Flow controller directly."""
        flow: FlowWeb | None = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        ok = flow.set_pressure(req.index, req.pressure_mbar)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pressure")
        return {"ok": True}

    @app.post("/api/control/flow/set_flow")
    def flow_set_flow_legacy(req: FlowSetFlowRequest):
        """Legacy endpoint - calls Flow controller directly."""
        flow: FlowWeb | None = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        ok = flow.set_flow(req.index, req.flow_ul_hr)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set flow")
        return {"ok": True}

    @app.post("/api/control/flow/set_mode")
    def flow_set_mode_legacy(req: FlowSetModeRequest):
        """Legacy endpoint - calls Flow controller directly."""
        flow: FlowWeb | None = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        from config import CONTROL_MODE_UI_TO_FIRMWARE

        firmware_mode = CONTROL_MODE_UI_TO_FIRMWARE.get(req.mode_ui, 0)
        ok = flow.set_control_mode(req.index, firmware_mode)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set control mode")
        return {"ok": True}

    @app.post("/api/control/flow/set_pi_consts")
    def flow_set_pi_legacy(req: FlowSetPIRequest):
        """Legacy endpoint - calls Flow controller directly."""
        flow: FlowWeb | None = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        ok = flow.set_flow_pi_consts(req.index, [req.p, req.i])
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set PI consts")
        return {"ok": True}

    @app.get("/api/control/heater/state", response_model=HeaterState)
    def heater_state_legacy():
        """Legacy endpoint - calls Heater controllers directly."""
        heaters: list[heater_web] | None = CONTROLLERS.get("heaters")
        if heaters is None:
            raise HTTPException(status_code=503, detail="Heaters unavailable")

        items: list[HeaterStateItem] = []
        for h in heaters:
            h.update()
            items.append(
                HeaterStateItem(
                    temp_c_actual=h.temp_c_actual,
                    temp_c_target=h.temp_c_target,
                    pid_enabled=h.pid_enabled,
                    stir_enabled=h.stir_enabled,
                    autotuning=h.autotuning,
                    status_text=h.status_text,
                )
            )
        return HeaterState(heaters=items)

    @app.post("/api/control/heater/set_temp")
    def heater_set_temp_legacy(req: HeaterSetTempRequest):
        """Legacy endpoint - calls Heater controller directly."""
        heaters: list[heater_web] | None = CONTROLLERS.get("heaters")
        if heaters is None or req.index >= len(heaters):
            raise HTTPException(status_code=503, detail="Heaters unavailable")
        heaters[req.index].set_temp(req.temp_c)
        return {"ok": True}

    @app.post("/api/control/heater/pid")
    def heater_set_pid_legacy(req: HeaterSetPidRequest):
        """Legacy endpoint - calls Heater controller directly."""
        heaters: list[heater_web] | None = CONTROLLERS.get("heaters")
        if heaters is None or req.index >= len(heaters):
            raise HTTPException(status_code=503, detail="Heaters unavailable")
        heaters[req.index].set_pid_running(1 if req.enabled else 0)
        heaters[req.index].pid_enabled = req.enabled
        return {"ok": True}

    @app.post("/api/control/heater/stir")
    def heater_set_stir_legacy(req: HeaterSetStirRequest):
        """Legacy endpoint - calls Heater controller directly."""
        heaters: list[heater_web] | None = CONTROLLERS.get("heaters")
        if heaters is None or req.index >= len(heaters):
            raise HTTPException(status_code=503, detail="Heaters unavailable")
        heaters[req.index].set_stir_running(1 if req.enabled else 0)
        heaters[req.index].stir_enabled = req.enabled
        return {"ok": True}

    @app.get("/api/streams/camera/snapshot")
    def camera_snapshot_legacy():
        """Legacy endpoint - uses Camera controller directly (snapshot is synchronous)."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        try:
            if cam.thread is None or not cam.thread.is_alive():
                cam.initialize()
            frame = cam.get_frame()
            if not frame:
                raise HTTPException(status_code=503, detail="No frame available")
            from fastapi.responses import Response
            return Response(content=frame, media_type="image/jpeg")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get snapshot: {e}") from e

    @app.post("/api/control/camera/set_resolution")
    def camera_set_resolution_legacy(req: CameraResolutionRequest):
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        params: dict[str, Any] = {}
        if req.preset:
            params["preset"] = req.preset
        if req.width and req.height:
            params["width"] = int(req.width)
            params["height"] = int(req.height)
        cam.on_cam({"cmd": CMD_SET_RESOLUTION, "parameters": params})
        return {"ok": True}

    @app.post("/api/control/camera/set_snapshot_resolution")
    def camera_set_snapshot_resolution_legacy(req: CameraSnapshotResolutionRequest):
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        params: dict[str, Any] = {"mode": req.mode}
        if req.width and req.height:
            params["width"] = int(req.width)
            params["height"] = int(req.height)
        cam.on_cam({"cmd": CMD_SET_SNAPSHOT_RESOLUTION, "parameters": params})
        return {"ok": True}

    @app.post("/api/control/camera/roi")
    def camera_set_roi_legacy(req: CameraROIRequest):
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_roi({"cmd": CMD_SET, "parameters": {"x": req.x, "y": req.y, "w": req.w, "h": req.h}})
        return {"ok": True}

    @app.post("/api/control/camera/roi/clear")
    def camera_clear_roi_legacy():
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_roi({"cmd": CMD_CLEAR, "parameters": {}})
        return {"ok": True}

    @app.post("/api/control/strobe/enable")
    def strobe_enable_legacy(req: StrobeEnableRequest):
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_strobe({"cmd": CMD_ENABLE, "parameters": {"on": 1 if req.on else 0}})
        return {"ok": True}

    @app.post("/api/control/strobe/hold")
    def strobe_hold_legacy(req: StrobeEnableRequest):
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_strobe({"cmd": CMD_HOLD, "parameters": {"on": 1 if req.on else 0}})
        return {"ok": True}

    @app.post("/api/control/strobe/timing")
    def strobe_timing_legacy(req: StrobeTimingRequest):
        """Legacy endpoint - calls Camera controller directly."""
        cam: Camera | None = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        params = {"period_ns": int(req.period_ns)}
        if req.wait_ns is not None:
            params["wait_ns"] = int(req.wait_ns)
        cam.on_strobe({"cmd": CMD_TIMING, "parameters": params})
        return {"ok": True}

    @app.post("/api/control/droplet/start")
    def droplet_start_legacy():
        """Legacy endpoint - calls Droplet controller directly."""
        droplet = CONTROLLERS.get("droplet")
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        ok = droplet.start()
        if not ok:
            raise HTTPException(
                status_code=400, detail="Failed to start droplet detection (check ROI)"
            )
        return {"ok": True}

    @app.post("/api/control/droplet/stop")
    def droplet_stop_legacy():
        """Legacy endpoint - calls Droplet controller directly."""
        droplet = CONTROLLERS.get("droplet")
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        droplet.stop()
        return {"ok": True}

    @app.get("/api/control/droplet/status")
    def droplet_status_legacy():
        """Legacy endpoint - calls Droplet controller directly."""
        droplet = CONTROLLERS.get("droplet")
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return {
            "running": droplet.running,
            "frame_count": droplet.frame_count,
            "droplet_count_total": droplet.droplet_count_total,
            "processing_rate_hz": round(getattr(droplet, "processing_rate_hz", 0.0), 2),
            "statistics": droplet.get_statistics(),
        }

    @app.get("/api/control/droplet/histogram")
    def droplet_histogram_legacy():
        """Legacy endpoint - calls Droplet controller directly."""
        droplet = CONTROLLERS.get("droplet")
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return droplet.get_histogram()

    @app.get("/api/control/droplet/statistics")
    def droplet_statistics_legacy():
        """Legacy endpoint - calls Droplet controller directly."""
        droplet = CONTROLLERS.get("droplet")
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return droplet.get_statistics()

    @app.get("/api/control/droplet/performance")
    def droplet_performance_legacy():
        """Legacy endpoint - calls Droplet controller directly."""
        droplet = CONTROLLERS.get("droplet")
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return droplet.get_performance_metrics()

    # Pump endpoints
    @app.get("/api/control/pump/state/{pump}")
    def pump_state_legacy(pump: str):
        """Legacy endpoint - calls Pump controller directly."""
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        return pump_ctrl.get_state(pump)

    @app.post("/api/control/pump/set_flow")
    def pump_set_flow_legacy(req: PumpSetFlowRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_flow(req.pump, req.flow)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump flow")
        return {"ok": True}

    @app.post("/api/control/pump/set_diameter")
    def pump_set_diameter_legacy(req: PumpSetDiameterRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_diameter(req.pump, req.diameter)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump diameter")
        return {"ok": True}

    @app.post("/api/control/pump/set_direction")
    def pump_set_direction_legacy(req: PumpSetDirectionRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_direction(req.pump, req.direction)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump direction")
        return {"ok": True}

    @app.post("/api/control/pump/set_state")
    def pump_set_state_legacy(req: PumpSetStateRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_state(req.pump, req.state)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump state")
        return {"ok": True}

    @app.post("/api/control/pump/set_unit")
    def pump_set_unit_legacy(req: PumpSetUnitRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_unit(req.pump, req.unit)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump unit")
        return {"ok": True}

    @app.post("/api/control/pump/set_gearbox")
    def pump_set_gearbox_legacy(req: PumpSetGearboxRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_gearbox(req.pump, req.gearbox)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump gearbox")
        return {"ok": True}

    @app.post("/api/control/pump/set_microstep")
    def pump_set_microstep_legacy(req: PumpSetMicrostepRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_microstep(req.pump, req.microstep)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump microstep")
        return {"ok": True}

    @app.post("/api/control/pump/set_threadrod")
    def pump_set_threadrod_legacy(req: PumpSetThreadrodRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_threadrod(req.pump, req.threadrod)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump threadrod")
        return {"ok": True}

    @app.post("/api/control/pump/set_enable")
    def pump_set_enable_legacy(req: PumpSetEnableRequest):
        pump_ctrl = CONTROLLERS.get("pump")
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        ok = pump_ctrl.set_enable(req.pump, req.enabled)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pump enable")
        return {"ok": True}

    @app.get("/api/config/channels", response_model=ChannelConfigResponse)
    def get_channels() -> ChannelConfigResponse:
        return ChannelConfigResponse(channels=ChannelConfig(**CHANNEL_CONFIG))

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
        return ChannelConfigResponse(channels=ChannelConfig(**CHANNEL_CONFIG))

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

