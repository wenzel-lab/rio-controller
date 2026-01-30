"""Pydantic models for API responses (skeleton)."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List


class HealthResponse(BaseModel):
    status: str = "ok"
    simulation: bool = False


class CapabilitiesResponse(BaseModel):
    modules: Dict[str, bool]
    simulation: bool
    notes: Dict[str, Any] | None = None


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
    heat_power_limit_pc: int | None = None
    autotune_status_text: str | None = None
    autotune_target_temp: float | None = None
    stir_speed_target: int | None = None
    stir_speed_text: str | None = None


class HeaterState(BaseModel):
    heaters: List[HeaterStateItem]


# Channel metadata (enable + naming)
class ChannelInfo(BaseModel):
    enabled: bool = True
    name: str = ""
    liquid_type: str = ""  # e.g., mineral_oil, fluorinated_novec, aqueous, custom
    calibration_factor: float | None = None


class ChannelConfig(BaseModel):
    flow: Dict[str, ChannelInfo] | None = None
    pressure: Dict[str, ChannelInfo] | None = None
    heater: Dict[str, ChannelInfo] | None = None


class ChannelConfigResponse(BaseModel):
    channels: ChannelConfig


# Capture control
class CaptureStartRequest(BaseModel):
    topics: List[str]
    channels: Dict[str, List[int]] | None = None
    path: str | None = None


class CaptureStatusResponse(BaseModel):
    enabled: bool
    path: str | None = None
    topics: List[str] = []
    channels: Dict[str, List[int]] | None = None


# Camera / Strobe / ROI requests
class CameraResolutionRequest(BaseModel):
    preset: str | None = None  # matches config.CAMERA_RESOLUTION_PRESETS keys
    width: int | None = None
    height: int | None = None


class CameraSnapshotResolutionRequest(BaseModel):
    mode: str  # display|full|custom
    width: int | None = None
    height: int | None = None


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
    display_width: int | None = None
    display_height: int | None = None
    snapshot_resolution_mode: str | None = None
    snapshot_width: int | None = None
    snapshot_height: int | None = None
    roi: dict | None = None


class StrobeEnableRequest(BaseModel):
    on: bool


class StrobeTimingRequest(BaseModel):
    period_ns: int
    wait_ns: int | None = None


class StrobeState(BaseModel):
    hold: int
    enable: int
    wait_ns: int
    period_ns: int
    framerate: int | float
    cam_read_time_us: int | float


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
    flow: float | None = None
    diameter: float | None = None
    direction: int | None = None  # -1 withdraw, 1 infuse
    state: bool | None = None  # True = running, False = stopped
    unit: str | None = None
    gearbox: str | None = None
    microstep: str | None = None
    threadrod: str | None = None
    enabled: bool | None = None
