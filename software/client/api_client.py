"""
Rio API client library for Python.

Provides a lightweight client for interacting with the Rio API server.
Supports both REST API calls and WebSocket streaming.
"""

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
import websocket

logger = logging.getLogger(__name__)


# Custom exception classes
class RioAPIError(Exception):
    """Base exception for Rio API errors."""

    pass


class RioConnectionError(RioAPIError):
    """Raised when connection to API server fails."""

    pass


class RioHTTPError(RioAPIError):
    """Raised when API returns an HTTP error."""

    def __init__(self, message: str, status_code: int, response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RioWebSocketError(RioAPIError):
    """Raised when WebSocket connection fails."""

    pass


class RioClient:
    """REST API client for Rio controller."""

    def __init__(
        self, base_url: str = "http://localhost:8000", timeout: float = 5.0, max_retries: int = 3
    ):
        """
        Initialize Rio API client.

        Args:
            base_url: Base URL of the API server (e.g., "http://192.168.1.100:8000")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures

        Example:
            >>> client = RioClient(base_url="http://192.168.1.100:8000")
            >>> state = client.get_flow_state()
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Internal GET request helper with retry logic."""
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                result: Dict[str, Any] = response.json()
                return result
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Request timeout (attempt {attempt + 1}/{self.max_retries}), retrying..."
                    )
                    time.sleep(0.5 * (attempt + 1))
                else:
                    raise RioConnectionError(
                        f"Request timeout after {self.max_retries} attempts: {e}"
                    ) from e
            except requests.exceptions.ConnectionError as e:
                raise RioConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
            except requests.exceptions.HTTPError as e:
                try:
                    error_detail = e.response.json()
                except (ValueError, AttributeError):
                    error_detail = {
                        "detail": e.response.text if hasattr(e.response, "text") else str(e)
                    }
                raise RioHTTPError(
                    f"HTTP {e.response.status_code}: {error_detail.get('detail', str(e))}",
                    status_code=e.response.status_code,
                    response=error_detail,
                ) from e
            except requests.exceptions.RequestException as e:
                raise RioAPIError(f"Request failed: {e}") from e

        raise RioConnectionError(
            f"Request failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Internal POST request helper with retry logic."""
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                result: Dict[str, Any] = response.json()
                return result
            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Request timeout (attempt {attempt + 1}/{self.max_retries}), retrying..."
                    )
                    time.sleep(0.5 * (attempt + 1))
                else:
                    raise RioConnectionError(
                        f"Request timeout after {self.max_retries} attempts: {e}"
                    ) from e
            except requests.exceptions.ConnectionError as e:
                raise RioConnectionError(f"Failed to connect to {self.base_url}: {e}") from e
            except requests.exceptions.HTTPError as e:
                try:
                    error_detail = e.response.json()
                except (ValueError, AttributeError):
                    error_detail = {
                        "detail": e.response.text if hasattr(e.response, "text") else str(e)
                    }
                raise RioHTTPError(
                    f"HTTP {e.response.status_code}: {error_detail.get('detail', str(e))}",
                    status_code=e.response.status_code,
                    response=error_detail,
                ) from e
            except requests.exceptions.RequestException as e:
                raise RioAPIError(f"Request failed: {e}") from e

        raise RioConnectionError(
            f"Request failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    # System endpoints
    def health(self) -> Dict[str, Any]:
        """Get API health status."""
        return self._get("/api/system/health")

    def capabilities(self) -> Dict[str, Any]:
        """Get available module capabilities."""
        return self._get("/api/system/capabilities")

    # Channel configuration
    def get_channels(self) -> Dict[str, Any]:
        """Get channel metadata (names, liquid types, calibration factors)."""
        return self._get("/api/config/channels")

    def set_channels(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update channel metadata (runtime-only, not persisted)."""
        return self._post("/api/config/channels", data=config)

    # Flow/pressure control
    def get_flow_state(self) -> Dict[str, Any]:
        """Get current flow/pressure state."""
        return self._get("/api/control/flow/state")

    def set_pressure(self, index: int, pressure_mbar: float) -> Dict[str, Any]:
        """Set pressure target for a channel."""
        return self._post(
            "/api/control/flow/set_pressure", data={"index": index, "pressure_mbar": pressure_mbar}
        )

    def set_flow(self, index: int, flow_ul_hr: float) -> Dict[str, Any]:
        """Set flow target for a channel."""
        return self._post(
            "/api/control/flow/set_flow", data={"index": index, "flow_ul_hr": flow_ul_hr}
        )

    def set_flow_mode(self, index: int, mode_ui: int) -> Dict[str, Any]:
        """Set control mode for a channel."""
        return self._post("/api/control/flow/set_mode", data={"index": index, "mode_ui": mode_ui})

    def set_flow_pi_consts(self, index: int, p: int, i: int) -> Dict[str, Any]:
        """Set PI controller constants for a channel."""
        return self._post("/api/control/flow/set_pi_consts", data={"index": index, "p": p, "i": i})

    # Heater control
    def get_heater_state(self) -> Dict[str, Any]:
        """Get current heater states."""
        return self._get("/api/control/heater/state")

    def set_heater_temp(self, index: int, temp_c: float) -> Dict[str, Any]:
        """Set target temperature for a heater."""
        return self._post("/api/control/heater/set_temp", data={"index": index, "temp_c": temp_c})

    def set_heater_pid(self, index: int, enabled: bool) -> Dict[str, Any]:
        """Enable/disable PID control for a heater."""
        return self._post("/api/control/heater/pid", data={"index": index, "enabled": enabled})

    def set_heater_stir(self, index: int, enabled: bool) -> Dict[str, Any]:
        """Enable/disable stirrer for a heater."""
        return self._post("/api/control/heater/stir", data={"index": index, "enabled": enabled})

    # Camera control
    def get_camera_snapshot(self) -> bytes:
        """Get JPEG snapshot from camera."""
        url = urljoin(self.base_url + "/", "/api/streams/camera/snapshot")
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            result: bytes = response.content
            return result
        except requests.exceptions.RequestException as e:
            raise RioAPIError(f"Failed to get camera snapshot: {e}") from e

    def set_camera_resolution(
        self,
        preset: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set camera display resolution."""
        data: Dict[str, Any] = {}
        if preset:
            data["preset"] = preset
        if width and height:
            data["width"] = width
            data["height"] = height
        return self._post("/api/control/camera/set_resolution", data=data)

    def set_camera_roi(self, x: int, y: int, w: int, h: int) -> Dict[str, Any]:
        """Set camera ROI."""
        return self._post("/api/control/camera/roi", data={"x": x, "y": y, "w": w, "h": h})

    def clear_camera_roi(self) -> Dict[str, Any]:
        """Clear camera ROI."""
        return self._post("/api/control/camera/roi/clear")

    # Strobe control
    def set_strobe_enable(self, enabled: bool) -> Dict[str, Any]:
        """Enable/disable strobe."""
        return self._post("/api/control/strobe/enable", data={"on": enabled})

    def set_strobe_hold(self, hold: bool) -> Dict[str, Any]:
        """Enable/disable strobe hold mode."""
        return self._post("/api/control/strobe/hold", data={"on": hold})

    def set_strobe_timing(self, period_ns: int, wait_ns: Optional[int] = None) -> Dict[str, Any]:
        """Set strobe timing parameters."""
        data: Dict[str, Any] = {"period_ns": period_ns}
        if wait_ns is not None:
            data["wait_ns"] = wait_ns
        return self._post("/api/control/strobe/timing", data=data)

    # Droplet detection
    def droplet_start(self) -> Dict[str, Any]:
        """Start droplet detection."""
        return self._post("/api/control/droplet/start")

    def droplet_stop(self) -> Dict[str, Any]:
        """Stop droplet detection."""
        return self._post("/api/control/droplet/stop")

    def droplet_status(self) -> Dict[str, Any]:
        """Get droplet detection status."""
        return self._get("/api/control/droplet/status")

    def droplet_histogram(self) -> Dict[str, Any]:
        """Get droplet histogram."""
        return self._get("/api/control/droplet/histogram")

    def droplet_statistics(self) -> Dict[str, Any]:
        """Get droplet statistics."""
        return self._get("/api/control/droplet/statistics")

    # Data capture
    def capture_start(
        self,
        topics: List[str],
        channels: Optional[Dict[str, List[int]]] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start CSV data capture."""
        data: Dict[str, Any] = {"topics": topics}
        if channels:
            data["channels"] = channels
        if path:
            data["path"] = path
        return self._post("/api/data/capture/start", data=data)

    def capture_stop(self) -> Dict[str, Any]:
        """Stop CSV data capture."""
        return self._post("/api/data/capture/stop")

    def capture_status(self) -> Dict[str, Any]:
        """Get capture status."""
        return self._get("/api/data/capture/status")


class RioStreamClient:
    """WebSocket client for Rio telemetry streaming with thread-safe message queue."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        reconnect: bool = True,
        max_queue_size: int = 1000,
    ):
        """
        Initialize WebSocket stream client.

        Args:
            base_url: Base URL of the API server
            reconnect: Automatically reconnect on disconnect (not yet implemented)
            max_queue_size: Maximum size of message queue

        Example:
            >>> stream = RioStreamClient(base_url="http://192.168.1.100:8000")
            >>> stream.subscribe(["flow"], channels={"flow": [0, 1]})
            >>> for msg in stream.iter_messages(timeout=10.0):
            ...     print(msg)
        """
        self.base_url = base_url.rstrip("/")
        self.reconnect = reconnect
        self.max_queue_size = max_queue_size
        self.ws: Optional[websocket.WebSocketApp] = None
        self.subscribed_topics: List[str] = []
        self.subscribed_channels: Dict[str, List[int]] = {}
        self.message_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.ws_thread: Optional[threading.Thread] = None
        self._connected = False
        self._stop_event = threading.Event()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close WebSocket."""
        self.close()
        return False

    def _get_ws_url(self) -> str:
        """Convert HTTP base URL to WebSocket URL."""
        if self.base_url.startswith("http://"):
            return self.base_url.replace("http://", "ws://") + "/api/streams/aggregate"
        elif self.base_url.startswith("https://"):
            return self.base_url.replace("https://", "wss://") + "/api/streams/aggregate"
        else:
            return f"ws://{self.base_url}/api/streams/aggregate"

    def subscribe(self, topics: List[str], channels: Optional[Dict[str, List[int]]] = None):
        """
        Subscribe to topics and channels.

        Args:
            topics: List of topics to subscribe to (e.g., ["flow", "pressure", "heater"])
            channels: Optional dict mapping topic to list of channel indices (e.g., {"flow": [0, 1]})
        """
        self.subscribed_topics = topics
        self.subscribed_channels = channels or {}

    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message - thread-safe queue."""
        try:
            data = json.loads(message)
            try:
                self.message_queue.put_nowait(data)
            except queue.Full:
                logger.warning("Message queue full, dropping message")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
        self._connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.info("WebSocket closed")
        self._connected = False

    def _on_open(self, ws):
        """Handle WebSocket open - send subscription."""
        self._connected = True
        if self.subscribed_topics:
            subscribe_msg = {
                "action": "subscribe",
                "topics": self.subscribed_topics,
                "channels": self.subscribed_channels,
            }
            try:
                ws.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to topics: {self.subscribed_topics}")
            except Exception as e:
                logger.error(f"Failed to send subscription: {e}")

    def connect(self):
        """Connect to WebSocket and start receiving messages in background thread."""
        if self.ws is not None and self._connected:
            logger.warning("WebSocket already connected")
            return

        url = self._get_ws_url()
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )

        # Start WebSocket in background thread
        self._stop_event.clear()
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()

        # Wait for connection (with timeout)
        timeout = 5.0
        start = time.time()
        while not self._connected and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not self._connected:
            raise RioWebSocketError(f"Failed to connect to {url} within {timeout}s")

    def _run_websocket(self):
        """Run WebSocket in background thread."""
        if self.ws is None:
            logger.error("WebSocket not initialized")
            return
        try:
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"WebSocket thread error: {e}")
            self._connected = False

    def iter_messages(self, timeout: Optional[float] = None):
        """
        Iterator over WebSocket messages.

        Args:
            timeout: Optional timeout in seconds

        Yields:
            Dict containing message data (topic, channel, timestamp, value, unit)

        Example:
            >>> stream = RioStreamClient()
            >>> stream.subscribe(["flow"])
            >>> for msg in stream.iter_messages(timeout=10.0):
            ...     print(f"{msg['topic']}: {msg['value']}")
        """
        if not self._connected:
            self.connect()

        start_time = time.time()
        while True:
            if timeout and (time.time() - start_time) > timeout:
                break

            try:
                # Non-blocking get with timeout
                msg = self.message_queue.get(timeout=0.1)
                yield msg
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error getting message: {e}")
                break

    def close(self):
        """Close WebSocket connection."""
        self._stop_event.set()
        self._connected = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1.0)
