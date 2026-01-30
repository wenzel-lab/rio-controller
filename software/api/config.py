"""
API-specific configuration (defaults + env overrides).

This is intentionally minimal for the initial skeleton. Later steps will add
ownership maps, stream rate limits, and auth tokens as needed.
"""

import os
from dataclasses import dataclass
from typing import Optional


def _get_bool(env_var: str, default: bool = False) -> bool:
    val = os.getenv(env_var)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class APISettings:
    host: str = os.getenv("RIO_API_HOST", "0.0.0.0")
    port: int = int(os.getenv("RIO_API_PORT", "8000"))
    cors_allow_all: bool = _get_bool("RIO_API_CORS_ALLOW_ALL", True)
    auth_token: Optional[str] = os.getenv("RIO_API_TOKEN")  # optional; add enforcement later
    simulation: bool = _get_bool("RIO_SIMULATION", False)


settings = APISettings()
