"""
Rio API client library.

Provides Python client for interacting with the Rio controller API.
"""

from client.api_client import (
    RioAPIError,
    RioClient,
    RioConnectionError,
    RioHTTPError,
    RioStreamClient,
    RioWebSocketError,
)

__all__ = [
    "RioClient",
    "RioStreamClient",
    "RioAPIError",
    "RioConnectionError",
    "RioHTTPError",
    "RioWebSocketError",
]

__version__ = "0.1.0"

