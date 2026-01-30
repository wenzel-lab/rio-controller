"""
Rio API client library for Python.

Provides a lightweight client for interacting with the Rio API server.
Supports both REST API calls and WebSocket streaming.

Two client implementations are available:
1. RioClient - Direct HTTP client using requests (simple, fast)
2. RioThingClient - WoT-compliant client using LabThings ThingClient (standard, auto-generated)
"""

import json
import logging
import queue
import threading
import time
from typing import Any, Dict, List, Optional, NoReturn, cast
from urllib.parse import urljoin

import requests
import websocket

# Try to import ThingClient - optional dependency
LTThingClient: Any
try:
    from labthings_fastapi.client import ThingClient as LTThingClient
    from labthings_fastapi.exceptions import (
        FailedToInvokeActionError,
        ServerActionError,
        ClientPropertyError,
    )

    HAS_LABTHINGS = True
except ImportError:
    HAS_LABTHINGS = False
    LTThingClient = None

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
    """REST API client for Rio controller (direct HTTP)."""

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

    def set_heater_power_limit(self, index: int, power_limit_pc: int) -> Dict[str, Any]:
        """Set heater power limit percent."""
        return self._post(
            "/api/control/heater/power_limit",
            data={"index": index, "power_limit_pc": int(power_limit_pc)},
        )

    def set_heater_autotune(self, index: int, enabled: bool, temp_c: float) -> Dict[str, Any]:
        """Enable/disable heater autotune."""
        return self._post(
            "/api/control/heater/autotune",
            data={"index": index, "enabled": enabled, "temp_c": float(temp_c)},
        )

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

    def set_camera_snapshot_resolution(
        self, mode: str, width: Optional[int] = None, height: Optional[int] = None
    ) -> Dict[str, Any]:
        """Set snapshot resolution mode."""
        data: Dict[str, Any] = {"mode": mode}
        if width and height:
            data["width"] = width
            data["height"] = height
        return self._post("/api/control/camera/set_snapshot_resolution", data=data)

    def get_camera_state(self) -> Dict[str, Any]:
        """Get current camera state."""
        return self._get("/api/control/camera/state")

    def set_camera_type(self, camera: str) -> Dict[str, Any]:
        """Select camera backend on the API server."""
        return self._post("/api/control/camera/select", data={"camera": camera})

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

    def get_strobe_state(self) -> Dict[str, Any]:
        """Get current strobe state."""
        return self._get("/api/control/strobe/state")

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
        """Get droplet size histogram."""
        return self._get("/api/control/droplet/histogram")

    def droplet_statistics(self) -> Dict[str, Any]:
        """Get droplet detection statistics."""
        return self._get("/api/control/droplet/statistics")

    # Data capture
    def capture_start(
        self,
        topics: List[str],
        channels: Optional[Dict[str, List[int]]] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start CSV capture of sensor data."""
        data: Dict[str, Any] = {"topics": topics}
        if channels:
            data["channels"] = channels
        if path:
            data["path"] = path
        return self._post("/api/data/capture/start", data=data)

    def capture_stop(self) -> Dict[str, Any]:
        """Stop CSV capture."""
        return self._post("/api/data/capture/stop")

    def capture_status(self) -> Dict[str, Any]:
        """Get capture status."""
        return self._get("/api/data/capture/status")


class RioThingClient:
    """WoT-compliant REST API client for Rio controller using LabThings ThingClient.

    This client uses LabThings ThingClient internally to provide WoT-compliant access
    to Rio Things. It provides the same interface as RioClient but uses WoT routes
    (e.g., /flow/, /heater/) instead of legacy routes (/api/control/*).

    Benefits:
    - WoT standard compliance
    - Auto-generated from Thing Descriptions
    - Type-safe from TD schemas
    - Future-proof (works with any WoT Thing)

    Trade-offs:
    - Uses httpx instead of requests (different dependency)
    - Actions use async polling (50-150ms extra delay per action)
    - Requires fetching Thing Descriptions on initialization (one extra HTTP request)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 5.0,
        max_retries: int = 3,
    ):
        """
        Initialize WoT-compliant Rio API client.

        Args:
            base_url: Base URL of the API server (e.g., "http://192.168.1.100:8000")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures (not used with ThingClient)

        Example:
            >>> client = RioThingClient(base_url="http://192.168.1.100:8000")
            >>> state = client.get_flow_state()
        """
        if not HAS_LABTHINGS:
            raise ImportError(
                "labthings_fastapi is required for RioThingClient. "
                "Install with: pip install labthings-fastapi"
            )

        import httpx

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Create httpx client
        self.http_client = httpx.Client(timeout=timeout)

        # Initialize Thing clients (lazy loading - only fetch TDs when needed)
        self._flow_thing: Optional[LTThingClient] = None
        self._heater_thing: Optional[LTThingClient] = None
        self._camera_thing: Optional[LTThingClient] = None
        self._droplet_thing: Optional[LTThingClient] = None
        self._pump_thing: Optional[LTThingClient] = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close client."""
        self.close()
        return False

    def close(self):
        """Close the HTTP client."""
        self.http_client.close()

    def _get_flow_thing(self) -> Any:
        """Get or create FlowThing client."""
        if self._flow_thing is None:
            try:
                self._flow_thing = LTThingClient.from_url(
                    f"{self.base_url}/flow/", client=self.http_client
                )
            except Exception as e:
                raise RioConnectionError(f"Failed to connect to FlowThing: {e}") from e
        return self._flow_thing

    def _get_heater_thing(self) -> Any:
        """Get or create HeaterThing client."""
        if self._heater_thing is None:
            try:
                self._heater_thing = LTThingClient.from_url(
                    f"{self.base_url}/heater/", client=self.http_client
                )
            except Exception as e:
                raise RioConnectionError(f"Failed to connect to HeaterThing: {e}") from e
        return self._heater_thing

    def _get_camera_thing(self) -> Any:
        """Get or create CameraThing client."""
        if self._camera_thing is None:
            try:
                self._camera_thing = LTThingClient.from_url(
                    f"{self.base_url}/camera/", client=self.http_client
                )
            except Exception as e:
                raise RioConnectionError(f"Failed to connect to CameraThing: {e}") from e
        return self._camera_thing

    def _get_droplet_thing(self) -> Any:
        """Get or create DropletThing client."""
        if self._droplet_thing is None:
            try:
                self._droplet_thing = LTThingClient.from_url(
                    f"{self.base_url}/droplet/", client=self.http_client
                )
            except Exception as e:
                raise RioConnectionError(f"Failed to connect to DropletThing: {e}") from e
        return self._droplet_thing

    def _handle_action_error(self, e: Exception) -> NoReturn:
        """Convert LabThings exceptions to Rio exceptions and re-raise."""
        if isinstance(e, FailedToInvokeActionError):
            raise RioAPIError(f"Failed to invoke action: {e}") from e
        elif isinstance(e, ServerActionError):
            raise RioAPIError(f"Action failed: {e}") from e
        elif isinstance(e, ClientPropertyError):
            raise RioAPIError(f"Property access failed: {e}") from e
        # Re-raise other exceptions as-is
        raise

    def _coerce_result(self, result: Any) -> Dict[str, Any]:
        if hasattr(result, "dict"):
            return cast(Dict[str, Any], result.dict())
        if hasattr(result, "model_dump"):
            return cast(Dict[str, Any], result.model_dump())
        return cast(Dict[str, Any], result)

    # System endpoints (use legacy routes for compatibility)
    def health(self) -> Dict[str, Any]:
        """Get API health status."""
        try:
            response = self.http_client.get(f"{self.base_url}/api/system/health")
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to get health: {e}") from e

    def capabilities(self) -> Dict[str, Any]:
        """Get available module capabilities."""
        try:
            response = self.http_client.get(f"{self.base_url}/api/system/capabilities")
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to get capabilities: {e}") from e

    # Channel configuration (use legacy routes)
    def get_channels(self) -> Dict[str, Any]:
        """Get channel metadata (names, liquid types, calibration factors)."""
        try:
            response = self.http_client.get(f"{self.base_url}/api/config/channels")
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to get channels: {e}") from e

    def set_channels(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update channel metadata (runtime-only, not persisted)."""
        try:
            response = self.http_client.post(f"{self.base_url}/api/config/channels", json=config)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to set channels: {e}") from e

    # Flow/pressure control (use WoT Thing)
    def get_flow_state(self) -> Dict[str, Any]:
        """Get current flow/pressure state."""
        try:
            flow_thing = self._get_flow_thing()
            state = flow_thing.state  # Property access (auto-converted to dict)
            return self._coerce_result(state)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"Failed to get flow state: {e}") from e

    def set_pressure(self, index: int, pressure_mbar: float) -> Dict[str, Any]:
        """Set pressure target for a channel."""
        try:
            flow_thing = self._get_flow_thing()
            result = flow_thing.set_pressure(index=index, pressure_mbar=pressure_mbar)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"Failed to set pressure: {e}") from e

    def set_flow(self, index: int, flow_ul_hr: float) -> Dict[str, Any]:
        """Set flow target for a channel."""
        try:
            flow_thing = self._get_flow_thing()
            result = flow_thing.set_flow(index=index, flow_ul_hr=flow_ul_hr)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_flow_mode(self, index: int, mode_ui: int) -> Dict[str, Any]:
        """Set control mode for a channel."""
        try:
            flow_thing = self._get_flow_thing()
            result = flow_thing.set_mode(index=index, mode_ui=mode_ui)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_flow_pi_consts(self, index: int, p: int, i: int) -> Dict[str, Any]:
        """Set PI controller constants for a channel."""
        try:
            flow_thing = self._get_flow_thing()
            result = flow_thing.set_pi_consts(index=index, p=p, i=i)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    # Heater control (use WoT Thing)
    def get_heater_state(self) -> Dict[str, Any]:
        """Get current heater states."""
        try:
            heater_thing = self._get_heater_thing()
            state = heater_thing.state
            return self._coerce_result(state)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_heater_temp(self, index: int, temp_c: float) -> Dict[str, Any]:
        """Set target temperature for a heater."""
        try:
            heater_thing = self._get_heater_thing()
            result = heater_thing.set_temp(index=index, temp_c=temp_c)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_heater_pid(self, index: int, enabled: bool) -> Dict[str, Any]:
        """Enable/disable PID control for a heater."""
        try:
            heater_thing = self._get_heater_thing()
            result = heater_thing.set_pid(index=index, enabled=enabled)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_heater_stir(self, index: int, enabled: bool) -> Dict[str, Any]:
        """Enable/disable stirrer for a heater."""
        try:
            heater_thing = self._get_heater_thing()
            result = heater_thing.set_stir(index=index, enabled=enabled)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    # Camera control (use WoT Thing)
    def get_camera_snapshot(self) -> bytes:
        """Get JPEG snapshot from camera."""
        try:
            camera_thing = self._get_camera_thing()
            blob = camera_thing.snapshot()  # Returns ClientBlobOutput
            # Download blob content
            response = self.http_client.get(blob.href)
            response.raise_for_status()
            return response.content
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_camera_resolution(
        self,
        preset: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set camera display resolution."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.set_resolution(preset=preset, width=width, height=height)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_camera_roi(self, x: int, y: int, w: int, h: int) -> Dict[str, Any]:
        """Set camera ROI."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.set_roi(x=x, y=y, w=w, h=h)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def clear_camera_roi(self) -> Dict[str, Any]:
        """Clear camera ROI."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.clear_roi()
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def record_roi_frames(self, frames: int) -> Dict[str, Any]:
        """Record a fixed number of ROI frames as JPEGs."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.record_roi_frames(frames=frames)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    # Strobe control (use WoT Thing)
    def set_strobe_enable(self, enabled: bool) -> Dict[str, Any]:
        """Enable/disable strobe."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.strobe_enable(on=enabled)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_strobe_hold(self, hold: bool) -> Dict[str, Any]:
        """Enable/disable strobe hold mode."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.strobe_hold(on=hold)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def set_strobe_timing(self, period_ns: int, wait_ns: Optional[int] = None) -> Dict[str, Any]:
        """Set strobe timing parameters."""
        try:
            camera_thing = self._get_camera_thing()
            result = camera_thing.strobe_timing(period_ns=period_ns, wait_ns=wait_ns)
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    # Droplet detection (use WoT Thing)
    def droplet_start(self) -> Dict[str, Any]:
        """Start droplet detection."""
        try:
            droplet_thing = self._get_droplet_thing()
            result = droplet_thing.start()
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def droplet_stop(self) -> Dict[str, Any]:
        """Stop droplet detection."""
        try:
            droplet_thing = self._get_droplet_thing()
            result = droplet_thing.stop()
            return self._coerce_result(result)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def droplet_status(self) -> Dict[str, Any]:
        """Get droplet detection status."""
        try:
            droplet_thing = self._get_droplet_thing()
            status = droplet_thing.status
            return self._coerce_result(status)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def droplet_histogram(self) -> Dict[str, Any]:
        """Get droplet size histogram."""
        try:
            droplet_thing = self._get_droplet_thing()
            histogram = droplet_thing.histogram
            return self._coerce_result(histogram)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    def droplet_statistics(self) -> Dict[str, Any]:
        """Get droplet detection statistics."""
        try:
            droplet_thing = self._get_droplet_thing()
            stats = droplet_thing.statistics
            return self._coerce_result(stats)
        except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
            self._handle_action_error(e)
        except Exception as e:
            raise RioAPIError(f"API call failed: {e}") from e

    # Data capture (use legacy routes - not part of Things)
    def capture_start(
        self,
        topics: List[str],
        channels: Optional[Dict[str, List[int]]] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start CSV capture of sensor data."""
        try:
            data: Dict[str, Any] = {"topics": topics}
            if channels:
                data["channels"] = channels
            if path:
                data["path"] = path
            response = self.http_client.post(f"{self.base_url}/api/data/capture/start", json=data)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to start capture: {e}") from e

    def capture_stop(self) -> Dict[str, Any]:
        """Stop CSV capture."""
        try:
            response = self.http_client.post(f"{self.base_url}/api/data/capture/stop")
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to stop capture: {e}") from e

    def capture_status(self) -> Dict[str, Any]:
        """Get capture status."""
        try:
            response = self.http_client.get(f"{self.base_url}/api/data/capture/status")
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except Exception as e:
            raise RioAPIError(f"Failed to get capture status: {e}") from e


# WebSocket client (works with both RioClient and RioThingClient)
class RioStreamClient:
    """WebSocket client for Rio API streaming.

    Streams real-time sensor data (flow, pressure, heater) via WebSocket.
    Works with both RioClient and RioThingClient.
    """

    def __init__(self, base_url: str = "http://localhost:8000", max_queue_size: int = 1000):
        """
        Initialize WebSocket stream client.

        Args:
            base_url: Base URL of the API server
            max_queue_size: Maximum size of message queue

        Example:
            >>> stream = RioStreamClient(base_url="http://192.168.1.100:8000")
            >>> stream.subscribe(["flow", "pressure"])
            >>> for msg in stream.iter_messages(timeout=10.0):
            ...     print(f"{msg['topic']}: {msg['value']}")
        """
        self.base_url = base_url.rstrip("/")
        self.max_queue_size = max_queue_size
        self.message_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.subscribed_topics: List[str] = []
        self.subscribed_channels: Dict[str, List[int]] = {}
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self._connected = False
        self._stop_event = threading.Event()

    def _get_ws_url(self) -> str:
        """Get WebSocket URL."""
        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_url}/api/streams/aggregate"

    def subscribe(
        self,
        topics: List[str],
        channels: Optional[Dict[str, List[int]]] = None,
    ) -> None:
        """
        Subscribe to topics and channels.

        Args:
            topics: List of topics to subscribe to (e.g., ["flow", "pressure", "heater"])
            channels: Optional dict mapping topic to list of channel indices
                     (e.g., {"flow": [0, 1], "pressure": [0, 2]})
        """
        self.subscribed_topics = topics
        self.subscribed_channels = channels or {}

    def _on_message(self, ws, message):
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            self.message_queue.put(data, block=False)
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
