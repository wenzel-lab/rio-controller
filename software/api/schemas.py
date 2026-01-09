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


class HeaterStateItem(BaseModel):
    temp_c_actual: float
    temp_c_target: float
    pid_enabled: bool
    stir_enabled: bool
    autotuning: bool
    status_text: str


class HeaterState(BaseModel):
    heaters: List[HeaterStateItem]


# Channel metadata (enable + naming)
class ChannelInfo(BaseModel):
    enabled: bool = True
    name: str = ""


class ChannelConfig(BaseModel):
    flow: Dict[str, ChannelInfo] | None = None
    pressure: Dict[str, ChannelInfo] | None = None
    heater: Dict[str, ChannelInfo] | None = None


class ChannelConfigResponse(BaseModel):
    channels: ChannelConfig



