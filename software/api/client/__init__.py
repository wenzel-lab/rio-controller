"""
Rio API client library.

Provides Python client for interacting with the Rio controller API.
"""

from .api_client import (
    RioAPIError,
    RioClient,
    RioConnectionError,
    RioHTTPError,
    RioStreamClient,
    RioThingClient,
    RioWebSocketError,
)
from .syringe_pump_api import PumpAPIError, SyringePumpAPI

__all__ = [
    "RioClient",
    "RioThingClient",
    "RioStreamClient",
    "RioAPIError",
    "RioConnectionError",
    "RioHTTPError",
    "RioWebSocketError",
    "SyringePumpAPI",
    "PumpAPIError",
]

__version__ = "0.1.0"
