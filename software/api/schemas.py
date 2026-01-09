"""Pydantic models for API responses (skeleton)."""

from pydantic import BaseModel
from typing import Dict, Any


class HealthResponse(BaseModel):
    status: str = "ok"
    simulation: bool = False


class CapabilitiesResponse(BaseModel):
    modules: Dict[str, bool]
    simulation: bool
    notes: Dict[str, Any] | None = None


