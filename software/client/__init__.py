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

__all__ = [
    "RioClient",
    "RioThingClient",
    "RioStreamClient",
    "RioAPIError",
    "RioConnectionError",
    "RioHTTPError",
    "RioWebSocketError",
]

__version__ = "0.1.0"
