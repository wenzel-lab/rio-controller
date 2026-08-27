"""Pydantic models for API responses (skeleton)."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union


class HealthResponse(BaseModel):
    status: str = "ok"
    simulation: bool = False


class CapabilitiesResponse(BaseModel):
    modules: Dict[str, bool]
    simulation: bool
    notes: Optional[Dict[str, Any]] = None


# Flow/pressure
class FlowSetPressureRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    pressure_mbar: float


class FlowSetFlowRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    flow_ul_hr: float


class FlowSetModeRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    mode_ui: int = Field(..., ge=0)


class FlowSetPIRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    p: int = Field(..., ge=0)
    i: int = Field(..., ge=0)


class FlowState(BaseModel):
    pressure_targets_mbar: List[float]
    pressure_actuals_mbar: List[float]
    flow_targets_ul_hr: List[float]
    flow_actuals_ul_hr: List[float]
    control_modes_ui: List[int]
    control_modes_text: List[str]


# Heater
class HeaterSetTempRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    temp_c: float


class HeaterSetPidRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    enabled: bool


class HeaterSetStirRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    enabled: bool


class HeaterSetPowerLimitRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    power_limit_pc: int = Field(..., ge=0, le=100)


class HeaterSetAutotuneRequest(BaseModel):
    index: int = Field(..., ge=0, le=3)
    enabled: bool
    temp_c: float


class HeaterStateItem(BaseModel):
    temp_c_actual: float
    temp_c_target: float
    pid_enabled: bool
    stir_enabled: bool
    autotuning: bool
    status_text: str
    heat_power_limit_pc: Optional[int] = None
    autotune_status_text: Optional[str] = None
    autotune_target_temp: Optional[float] = None
    stir_speed_target: Optional[int] = None
    stir_speed_text: Optional[str] = None


class HeaterState(BaseModel):
    heaters: List[HeaterStateItem]


# Channel metadata (enable + naming)
class ChannelInfo(BaseModel):
    enabled: bool = True
    name: str = ""
    liquid_type: str = ""  # e.g., mineral_oil, fluorinated_novec, aqueous, custom
    calibration_factor: Optional[float] = None


class ChannelConfig(BaseModel):
    flow: Optional[Dict[str, ChannelInfo]] = None
    pressure: Optional[Dict[str, ChannelInfo]] = None
    heater: Optional[Dict[str, ChannelInfo]] = None


class ChannelConfigResponse(BaseModel):
    channels: ChannelConfig


# Capture control
class CaptureStartRequest(BaseModel):
    topics: List[str]
    channels: Optional[Dict[str, List[int]]] = None
    path: Optional[str] = None


class CaptureStatusResponse(BaseModel):
    enabled: bool
    path: Optional[str] = None
    topics: List[str] = []
    channels: Optional[Dict[str, List[int]]] = None


# Camera / Strobe / ROI requests
class CameraResolutionRequest(BaseModel):
    preset: Optional[str] = None  # matches config.CAMERA_RESOLUTION_PRESETS keys
    width: Optional[int] = None
    height: Optional[int] = None


class CameraSnapshotResolutionRequest(BaseModel):
    mode: str  # display|full|custom
    width: Optional[int] = None
    height: Optional[int] = None


class CameraROIRequest(BaseModel):
    x: int
    y: int
    w: int
    h: int


class CameraSelectRequest(BaseModel):
    camera: str


class CameraState(BaseModel):
    camera: str
    status: str
    display_width: Optional[int] = None
    display_height: Optional[int] = None
    snapshot_resolution_mode: Optional[str] = None
    snapshot_width: Optional[int] = None
    snapshot_height: Optional[int] = None
    roi: Optional[dict] = None


class StrobeEnableRequest(BaseModel):
    on: bool


class StrobeTimingRequest(BaseModel):
    period_ns: int
    wait_ns: Optional[int] = None


class StrobeTriggerModeRequest(BaseModel):
    """hardware=True: camera LineOut triggers PIC flash (hybrid sync)."""

    hardware: bool


class StrobeState(BaseModel):
    hold: int
    enable: int
    wait_ns: int
    period_ns: int
    framerate: Union[int, float]
    cam_read_time_us: Union[int, float]
    trigger_mode: Optional[int] = None


# Pump (syringe pump)
class PumpSetFlowRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")  # A, B, C, or D
    flow: float = Field(..., gt=0)


class PumpSetDiameterRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    diameter: float = Field(..., gt=0)


class PumpSetDirectionRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    direction: int = Field(..., ge=-1, le=1)  # -1 withdraw, 1 infuse


class PumpSetStateRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    state: bool  # True = RUN, False = STOP


class PumpSetUnitRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    unit: str = Field(..., pattern="^(UL/MIN|UL/HR|ML/MIN|ML/HR)$")


class PumpSetGearboxRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    gearbox: str = Field(..., pattern="^(1:1|25:1|100:1)$")


class PumpSetMicrostepRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    microstep: str = Field(..., pattern="^(1/8|1/16|1/32|1/64)$")


class PumpSetThreadrodRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    threadrod: str = Field(..., pattern="^(1-START|4-START)$")


class PumpSetEnableRequest(BaseModel):
    pump: str = Field(..., pattern="^[A-D]$")
    enabled: bool


class PumpState(BaseModel):
    pump: str
    flow: Optional[float] = None
    diameter: Optional[float] = None
    direction: Optional[int] = None  # -1 withdraw, 1 infuse
    state: Optional[bool] = None  # True = running, False = stopped
    unit: Optional[str] = None
    gearbox: Optional[str] = None
    microstep: Optional[str] = None
    threadrod: Optional[str] = None
    enabled: Optional[bool] = None
