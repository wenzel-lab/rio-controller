"""
Syringe pump API client.

This is a lightweight client intended for Jupyter notebooks and scripts that
need to control external syringe pumps through the Rio API server.
It supports:
- WoT/LabThings pump Thing at /pump/ (preferred)
- Legacy REST endpoints under /api/control/pump/* (fallback)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast
from urllib.parse import urljoin

import requests

LTThingClient: Any
FailedToInvokeActionError: Any
ServerActionError: Any
ClientPropertyError: Any

try:
    from labthings_fastapi.client import ThingClient as LTThingClient
    try:
        from labthings_fastapi.exceptions import (
            FailedToInvokeActionError,
            ServerActionError,
            ClientPropertyError,
        )
    except ModuleNotFoundError:  # pragma: no cover - older labthings versions
        FailedToInvokeActionError = RuntimeError
        ServerActionError = RuntimeError
        ClientPropertyError = RuntimeError

    HAS_LABTHINGS = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_LABTHINGS = False
    LTThingClient = None
    FailedToInvokeActionError = Exception
    ServerActionError = Exception
    ClientPropertyError = Exception

logger = logging.getLogger(__name__)


class PumpAPIError(Exception):
    """Base exception for pump API errors."""


class PumpConnectionError(PumpAPIError):
    """Raised when connection to the pump API fails."""


class PumpActionError(PumpAPIError):
    """Raised when a pump action fails."""


class SyringePumpAPI:
    """Client for syringe pump control through the Rio API server."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 5.0,
        use_wot: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.use_wot = use_wot and HAS_LABTHINGS
        self.session = requests.Session()
        self._pump_thing: Optional[Any] = None
        self._http_client = None

        if use_wot and not HAS_LABTHINGS:
            logger.warning(
                "labthings_fastapi not installed; falling back to legacy pump endpoints."
            )

        if self.use_wot:
            import httpx

            self._http_client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close HTTP sessions."""
        self.session.close()
        if self._http_client is not None:
            self._http_client.close()

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except requests.exceptions.RequestException as e:
            raise PumpConnectionError(f"GET {url} failed: {e}") from e

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
        except requests.exceptions.RequestException as e:
            raise PumpConnectionError(f"POST {url} failed: {e}") from e

    def _coerce_result(self, result: Any) -> Dict[str, Any]:
        if hasattr(result, "dict"):
            return cast(Dict[str, Any], result.dict())
        if hasattr(result, "model_dump"):
            return cast(Dict[str, Any], result.model_dump())
        return cast(Dict[str, Any], result)

    def _get_pump_thing(self) -> Any:
        if not self.use_wot:
            raise PumpAPIError("WoT client not available (labthings_fastapi missing).")
        if self._pump_thing is None:
            try:
                self._pump_thing = LTThingClient.from_url(
                    f"{self.base_url}/pump/", client=self._http_client
                )
            except Exception as e:
                raise PumpConnectionError(f"Failed to connect to PumpThing: {e}") from e
        return self._pump_thing

    def _call_action(
        self, name: str, payload: Dict[str, Any], legacy_endpoint: str
    ) -> Dict[str, Any]:
        if self.use_wot:
            try:
                pump_thing = self._get_pump_thing()
                action = getattr(pump_thing, name)
                result = action(**payload)
                return self._coerce_result(result)
            except AttributeError:
                # Fallback to legacy if action doesn't exist in Thing
                return self._post(legacy_endpoint, payload)
            except (FailedToInvokeActionError, ServerActionError, ClientPropertyError) as e:
                raise PumpActionError(f"Pump action {name} failed: {e}") from e
            except Exception as e:
                raise PumpAPIError(f"Pump action {name} failed: {e}") from e
        return self._post(legacy_endpoint, payload)

    def get_state(self, pump: Optional[str] = None) -> Dict[str, Any]:
        """Get pump state. For legacy endpoints, pump must be provided."""
        if self.use_wot:
            state = self._coerce_result(self._get_pump_thing().state)
            if pump is None:
                return state
            if isinstance(state, dict):
                if pump in state:
                    return cast(Dict[str, Any], state[pump])
                pumps = state.get("pumps")
                if isinstance(pumps, dict) and pump in pumps:
                    return cast(Dict[str, Any], pumps[pump])
            return {"pump": pump, "state": state}
        if pump is None:
            raise PumpAPIError("Pump ID required for legacy pump state endpoint.")
        return self._get(f"/api/control/pump/state/{pump}")

    def set_flow(self, pump: str, flow: float) -> Dict[str, Any]:
        return self._call_action(
            "set_flow",
            {"pump": pump, "flow": flow},
            "/api/control/pump/set_flow",
        )

    def set_diameter(self, pump: str, diameter: float) -> Dict[str, Any]:
        return self._call_action(
            "set_diameter",
            {"pump": pump, "diameter": diameter},
            "/api/control/pump/set_diameter",
        )

    def set_direction(self, pump: str, direction: str) -> Dict[str, Any]:
        direction_value: Any = direction
        if isinstance(direction, str):
            value = direction.strip().lower()
            if value in ("infuse", "in", "forward", "1"):
                direction_value = 1
            elif value in ("withdraw", "retract", "out", "-1"):
                direction_value = -1
        return self._call_action(
            "set_direction",
            {"pump": pump, "direction": direction_value},
            "/api/control/pump/set_direction",
        )

    def set_state(self, pump: str, state: str) -> Dict[str, Any]:
        state_value: Any = state
        if isinstance(state, str):
            value = state.strip().lower()
            if value in ("run", "start", "on", "1", "true"):
                state_value = True
            elif value in ("stop", "off", "0", "false"):
                state_value = False
        return self._call_action(
            "set_state",
            {"pump": pump, "state": state_value},
            "/api/control/pump/set_state",
        )

    def set_unit(self, pump: str, unit: str) -> Dict[str, Any]:
        return self._call_action(
            "set_unit",
            {"pump": pump, "unit": unit},
            "/api/control/pump/set_unit",
        )

    def set_gearbox(self, pump: str, gearbox: str) -> Dict[str, Any]:
        return self._call_action(
            "set_gearbox",
            {"pump": pump, "gearbox": gearbox},
            "/api/control/pump/set_gearbox",
        )

    def set_microstep(self, pump: str, microstep: str) -> Dict[str, Any]:
        return self._call_action(
            "set_microstep",
            {"pump": pump, "microstep": microstep},
            "/api/control/pump/set_microstep",
        )

    def set_threadrod(self, pump: str, threadrod: str) -> Dict[str, Any]:
        return self._call_action(
            "set_threadrod",
            {"pump": pump, "threadrod": threadrod},
            "/api/control/pump/set_threadrod",
        )

    def set_enable(self, pump: str, enabled: bool) -> Dict[str, Any]:
        return self._call_action(
            "set_enable",
            {"pump": pump, "enabled": enabled},
            "/api/control/pump/set_enable",
        )
