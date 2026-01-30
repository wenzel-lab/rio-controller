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
from typing import Any, Optional, cast

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from api.config import settings
from api.schemas import (
    HealthResponse,
    CapabilitiesResponse,
    ChannelConfig,
    ChannelConfigResponse,
    CameraResolutionRequest,
    CameraSnapshotResolutionRequest,
    CameraROIRequest,
    StrobeEnableRequest,
    StrobeTimingRequest,
    FlowSetPressureRequest,
    FlowSetFlowRequest,
    FlowSetModeRequest,
    FlowSetPIRequest,
    FlowState,
    HeaterSetTempRequest,
    HeaterSetPidRequest,
    HeaterSetStirRequest,
    HeaterState,
    HeaterStateItem,
    CaptureStartRequest,
    CaptureStatusResponse,
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
from config import (  # noqa: E402
    CONTROL_MODE_UI_TO_FIRMWARE,
    CONTROL_MODE_FIRMWARE_TO_UI,
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

    return cap, controllers


# Initialize controllers once at import time (simple singleton style)
CAPABILITIES, CONTROLLERS = _init_controllers()

# Load channel metadata from main config file (single user-facing file)
CONFIG_FILE_PATH = os.getenv("RIO_CONFIG_FILE", "rio-config.yaml")


def _load_channels_from_yaml() -> dict[str, dict[str, dict[str, Any]]]:
    """
    Load channel metadata (enable/name/liquid_type/calibration_factor) from the main config YAML.
    Example structure:
    channels:
      flow:
        "0":
          liquid_type: mineral_oil
          calibration_factor: 1.05
          name: oil
        "1":
          liquid_type: aqueous
      pressure:
        "0":
          calibration_factor: 1.00
      heater:
        "0":
          name: tip-heater
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        return {}
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        return data.get("channels", {}) or {}
    except Exception as e:
        logger.warning("Failed to load channel config from %s: %s", CONFIG_FILE_PATH, e)
        return {}


# In-memory channel config (merge defaults + YAML)
def _default_channel_map() -> dict[str, dict[str, dict[str, Any]]]:
    # channels 0-3 for flow/pressure; 0-3 for heater
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


def create_app() -> FastAPI:  # noqa: C901
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
        return CapabilitiesResponse(
            modules=CAPABILITIES, simulation=settings.simulation, notes=notes
        )

    # ----------------------------
    # Channel metadata (enable/naming)
    # ----------------------------

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
                # calibration factor stays in-memory for now (future: persist)
                if getattr(v, "calibration_factor", None) is not None:
                    CHANNEL_CONFIG[topic][k]["calibration_factor"] = float(v.calibration_factor)
        return ChannelConfigResponse(channels=ChannelConfig(**cast(dict[str, Any], CHANNEL_CONFIG)))

    # ----------------------------
    # Flow / Pressure endpoints
    # ----------------------------

    @app.get("/api/control/flow/state", response_model=FlowState)
    def flow_state() -> FlowState:
        flow: Optional[FlowWeb] = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")

        # Get all values at once (returns tuple: valid, list[float])
        ok_p, pressure_actuals = flow.flow.get_pressure_actual()
        if not ok_p:
            pressure_actuals = [0.0] * flow.flow.NUM_CONTROLLERS
        ok_f, flow_actuals = flow.flow.get_flow_actual()
        if not ok_f:
            flow_actuals = [0.0] * flow.flow.NUM_CONTROLLERS

        # update cached targets/modes
        flow.get_pressure_targets()
        flow.get_flow_targets()
        flow.get_control_modes()

        return FlowState(
            pressure_targets_mbar=flow.pressure_mbar_targets,
            pressure_actuals_mbar=pressure_actuals,
            flow_targets_ul_hr=flow.flow_ul_hr_targets,
            flow_actuals_ul_hr=flow_actuals,
            control_modes_ui=[CONTROL_MODE_FIRMWARE_TO_UI.get(m, 0) for m in flow.control_modes],
            control_modes_text=flow.control_modes_text,
        )

    @app.post("/api/control/flow/set_pressure")
    def flow_set_pressure(req: FlowSetPressureRequest):
        flow: Optional[FlowWeb] = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        ok = flow.set_pressure(req.index, req.pressure_mbar)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set pressure")
        return {"ok": True}

    @app.post("/api/control/flow/set_flow")
    def flow_set_flow(req: FlowSetFlowRequest):
        flow: Optional[FlowWeb] = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        ok = flow.set_flow(req.index, req.flow_ul_hr)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set flow")
        return {"ok": True}

    @app.post("/api/control/flow/set_mode")
    def flow_set_mode(req: FlowSetModeRequest):
        flow: Optional[FlowWeb] = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        firmware_mode = CONTROL_MODE_UI_TO_FIRMWARE.get(req.mode_ui, 0)
        ok = flow.set_control_mode(req.index, firmware_mode)
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set control mode")
        return {"ok": True}

    @app.post("/api/control/flow/set_pi_consts")
    def flow_set_pi(req: FlowSetPIRequest):
        flow: Optional[FlowWeb] = CONTROLLERS.get("flow")
        if flow is None:
            raise HTTPException(status_code=503, detail="Flow controller unavailable")
        ok = flow.set_flow_pi_consts(req.index, [req.p, req.i])
        if not ok:
            raise HTTPException(status_code=400, detail="Failed to set PI consts")
        return {"ok": True}

    # ----------------------------
    # Heater endpoints
    # ----------------------------

    @app.get("/api/control/heater/state", response_model=HeaterState)
    def heater_state():
        heaters: Optional[list[heater_web]] = CONTROLLERS.get("heaters")
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
    def heater_set_temp(req: HeaterSetTempRequest):
        heaters: Optional[list[heater_web]] = CONTROLLERS.get("heaters")
        if heaters is None or req.index >= len(heaters):
            raise HTTPException(status_code=503, detail="Heaters unavailable")
        heaters[req.index].set_temp(req.temp_c)
        return {"ok": True}

    @app.post("/api/control/heater/pid")
    def heater_set_pid(req: HeaterSetPidRequest):
        heaters: Optional[list[heater_web]] = CONTROLLERS.get("heaters")
        if heaters is None or req.index >= len(heaters):
            raise HTTPException(status_code=503, detail="Heaters unavailable")
        heaters[req.index].set_pid_running(1 if req.enabled else 0)
        heaters[req.index].pid_enabled = req.enabled
        return {"ok": True}

    @app.post("/api/control/heater/stir")
    def heater_set_stir(req: HeaterSetStirRequest):
        heaters: Optional[list[heater_web]] = CONTROLLERS.get("heaters")
        if heaters is None or req.index >= len(heaters):
            raise HTTPException(status_code=503, detail="Heaters unavailable")
        heaters[req.index].set_stir_running(1 if req.enabled else 0)
        heaters[req.index].stir_enabled = req.enabled
        return {"ok": True}

    # ----------------------------
    # Camera snapshot
    # ----------------------------

    @app.get("/api/streams/camera/snapshot")
    def camera_snapshot():
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        if cam.thread is None or not cam.thread.is_alive():
            cam.initialize()
        frame = cam.get_frame()
        if not frame:
            raise HTTPException(status_code=503, detail="No frame available")
        return Response(content=frame, media_type="image/jpeg")

    @app.post("/api/control/camera/set_resolution")
    def camera_set_resolution(req: CameraResolutionRequest):
        cam: Optional[Camera] = CONTROLLERS.get("camera")
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
    def camera_set_snapshot_resolution(req: CameraSnapshotResolutionRequest):
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        params: dict[str, Any] = {"mode": req.mode}
        if req.width and req.height:
            params["width"] = int(req.width)
            params["height"] = int(req.height)
        cam.on_cam({"cmd": CMD_SET_SNAPSHOT_RESOLUTION, "parameters": params})
        return {"ok": True}

    @app.post("/api/control/camera/roi")
    def camera_set_roi(req: CameraROIRequest):
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_roi({"cmd": CMD_SET, "parameters": {"x": req.x, "y": req.y, "w": req.w, "h": req.h}})
        return {"ok": True}

    @app.post("/api/control/camera/roi/clear")
    def camera_clear_roi():
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_roi({"cmd": CMD_CLEAR, "parameters": {}})
        return {"ok": True}

    @app.post("/api/control/strobe/enable")
    def strobe_enable(req: StrobeEnableRequest):
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_strobe({"cmd": CMD_ENABLE, "parameters": {"on": 1 if req.on else 0}})
        return {"ok": True}

    @app.post("/api/control/strobe/hold")
    def strobe_hold(req: StrobeEnableRequest):
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        cam.on_strobe({"cmd": CMD_HOLD, "parameters": {"on": 1 if req.on else 0}})
        return {"ok": True}

    @app.post("/api/control/strobe/timing")
    def strobe_timing(req: StrobeTimingRequest):
        cam: Optional[Camera] = CONTROLLERS.get("camera")
        if cam is None:
            raise HTTPException(status_code=503, detail="Camera unavailable")
        params = {"period_ns": int(req.period_ns)}
        if req.wait_ns is not None:
            params["wait_ns"] = int(req.wait_ns)
        cam.on_strobe({"cmd": CMD_TIMING, "parameters": params})
        return {"ok": True}

    # ----------------------------
    # Droplet endpoints
    # ----------------------------

    def _get_droplet():
        return CONTROLLERS.get("droplet")

    @app.post("/api/control/droplet/start")
    def droplet_start():
        droplet = _get_droplet()
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        ok = droplet.start()
        if not ok:
            raise HTTPException(
                status_code=400, detail="Failed to start droplet detection (check ROI)"
            )
        return {"ok": True}

    @app.post("/api/control/droplet/stop")
    def droplet_stop():
        droplet = _get_droplet()
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        droplet.stop()
        return {"ok": True}

    @app.get("/api/control/droplet/status")
    def droplet_status():
        droplet = _get_droplet()
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
    def droplet_histogram():
        droplet = _get_droplet()
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return droplet.get_histogram()

    @app.get("/api/control/droplet/statistics")
    def droplet_statistics():
        droplet = _get_droplet()
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return droplet.get_statistics()

    @app.get("/api/control/droplet/performance")
    def droplet_performance():
        droplet = _get_droplet()
        if droplet is None:
            raise HTTPException(status_code=503, detail="Droplet controller unavailable")
        return droplet.get_performance_metrics()

    # ----------------------------
    # Pump (syringe pump) endpoints
    # ----------------------------

    def _get_pump():
        """Get pump controller if available."""
        return CONTROLLERS.get("pump")

    @app.get("/api/control/pump/state/{pump}")
    def pump_state(pump: str):
        """Get current state for a pump (A, B, C, or D)."""
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        if pump not in ["A", "B", "C", "D"]:
            raise HTTPException(status_code=400, detail="Pump must be A, B, C, or D")
        # When pump controller is implemented, call methods like:
        # flow = pump_ctrl.get_flow(pump)
        # diameter = pump_ctrl.get_diameter(pump)
        # etc.
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_flow")
    def pump_set_flow(req: PumpSetFlowRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_flow(req.pump, req.flow)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_diameter")
    def pump_set_diameter(req: PumpSetDiameterRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_diameter(req.pump, req.diameter)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_direction")
    def pump_set_direction(req: PumpSetDirectionRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_direction(req.pump, req.direction)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_state")
    def pump_set_state(req: PumpSetStateRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_state(req.pump, req.state)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_unit")
    def pump_set_unit(req: PumpSetUnitRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_unit(req.pump, req.unit)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_gearbox")
    def pump_set_gearbox(req: PumpSetGearboxRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_gearbox(req.pump, req.gearbox)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_microstep")
    def pump_set_microstep(req: PumpSetMicrostepRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_microstep(req.pump, req.microstep)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_threadrod")
    def pump_set_threadrod(req: PumpSetThreadrodRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_threadrod(req.pump, req.threadrod)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    @app.post("/api/control/pump/set_enable")
    def pump_set_enable(req: PumpSetEnableRequest):
        pump_ctrl = _get_pump()
        if pump_ctrl is None:
            raise HTTPException(status_code=503, detail="Pump controller unavailable")
        # When implemented: ok = pump_ctrl.set_enable(req.pump, req.enabled)
        raise HTTPException(status_code=501, detail="Pump controller not yet implemented")

    # ----------------------------
    # WS Aggregator
    # ----------------------------

    @app.websocket("/api/streams/aggregate")
    async def aggregate_ws(websocket):
        await AGGREGATOR.handle_ws(websocket)

    # ----------------------------
    # Capture control (flow/pressure/heater)
    # ----------------------------

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
