"""Remote pump controller adapter (API-backed)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from api.client import SyringePumpAPI, PumpAPIError

logger = logging.getLogger(__name__)

PUMP_IDS = ["A", "B", "C", "D"]


class RemotePumpController:
    """API-backed adapter that mimics PumpController for the Flask UI."""

    def __init__(self, base_url: str) -> None:
        self._client = SyringePumpAPI(base_url=base_url)

    def close(self) -> None:
        self._client.close()

    def get_state(self, pump: str) -> Dict[str, Any]:
        return self._client.get_state(pump)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        states: Dict[str, Dict[str, Any]] = {}
        for pump in PUMP_IDS:
            try:
                states[pump] = self.get_state(pump)
            except PumpAPIError as exc:
                logger.warning("Remote pump state failed for %s: %s", pump, exc)
        return states

    def set_flow(self, pump: str, flow: float) -> bool:
        self._client.set_flow(pump, flow)
        return True

    def set_diameter(self, pump: str, diameter: float) -> bool:
        self._client.set_diameter(pump, diameter)
        return True

    def set_direction(self, pump: str, direction: Any) -> bool:
        self._client.set_direction(pump, direction)
        return True

    def set_state(self, pump: str, state: Any) -> bool:
        self._client.set_state(pump, state)
        return True

    def set_unit(self, pump: str, unit: str) -> bool:
        self._client.set_unit(pump, unit)
        return True

    def set_gearbox(self, pump: str, gearbox: str) -> bool:
        self._client.set_gearbox(pump, gearbox)
        return True

    def set_microstep(self, pump: str, microstep: str) -> bool:
        self._client.set_microstep(pump, microstep)
        return True

    def set_threadrod(self, pump: str, threadrod: str) -> bool:
        self._client.set_threadrod(pump, threadrod)
        return True

    def set_enable(self, pump: str, enabled: bool) -> bool:
        self._client.set_enable(pump, enabled)
        return True
