"""Remote heater controller adapter (API-backed)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from api.client import RioClient, RioAPIError

logger = logging.getLogger(__name__)


class RemoteHeater:
    """API-backed adapter that mimics heater_web for the Flask UI."""

    pid_status_str = ["Unconfigured", "Idle", "Heating", "Suspended", "Error"]
    autotune_status_str = ["None", "Running", "Aborted", "Finished", "Failed"]

    def __init__(self, index: int, client: RioClient) -> None:
        self.index = index
        self._client = client
        self.autotuning = False
        self.pid_enabled = False
        self.stir_enabled = False
        self.autotune_target_temp = 50.0
        self.stir_target_speed = 0
        self.temp_c_actual = 0.0
        self.temp_c_target = 0.0
        self.status_text = ""
        self.autotune_status_text = ""
        self.temp_text = ""
        self.stir_speed_text = ""
        self.heat_power_limit_pc = 0
        self.enabled = True
        self.update()

    def _apply_state(self, state: Dict[str, Any]) -> None:
        self.temp_c_actual = float(state.get("temp_c_actual", 0.0) or 0.0)
        self.temp_c_target = float(state.get("temp_c_target", 0.0) or 0.0)
        self.pid_enabled = bool(state.get("pid_enabled", False))
        self.stir_enabled = bool(state.get("stir_enabled", False))
        self.autotuning = bool(state.get("autotuning", False))
        self.status_text = state.get("status_text", "Connected")
        self.heat_power_limit_pc = int(
            state.get("heat_power_limit_pc", self.heat_power_limit_pc) or 0
        )
        self.autotune_status_text = state.get("autotune_status_text", self.autotune_status_text)
        self.autotune_target_temp = float(
            state.get("autotune_target_temp", self.autotune_target_temp) or 0.0
        )
        self.stir_target_speed = int(state.get("stir_speed_target", self.stir_target_speed) or 0)
        self.stir_speed_text = state.get("stir_speed_text", self.stir_speed_text) or ""
        if not self.stir_speed_text:
            self.stir_speed_text = f"{self.stir_target_speed} RPS"
        self.temp_text = f"{round(self.temp_c_actual, 2)} / {round(self.temp_c_target, 2)}"

    def update(self) -> None:
        """Fetch heater state from API and update cached fields."""
        if not self.enabled:
            self.status_text = "Offline"
            return
        try:
            state = self._client.get_heater_state()
            heaters = state.get("heaters", [])
            if self.index < len(heaters):
                self._apply_state(heaters[self.index])
            else:
                self.status_text = "Unavailable"
        except RioAPIError as exc:
            logger.warning("Remote heater update failed: %s", exc)
            self.status_text = "Offline"

    def set_temp(self, temp: float) -> bool:
        try:
            self._client.set_heater_temp(self.index, float(temp))
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_temp failed: %s", exc)
            return False

    def set_pid_running(self, run: bool) -> bool:
        try:
            self._client.set_heater_pid(self.index, bool(run))
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_pid_running failed: %s", exc)
            return False

    def set_stir_running(self, run: bool) -> bool:
        try:
            self._client.set_heater_stir(self.index, bool(run))
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_stir_running failed: %s", exc)
            return False

    def set_heat_power_limit_pc(self, power_limit_pc: int) -> bool:
        try:
            self._client.set_heater_power_limit(self.index, int(power_limit_pc))
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_heat_power_limit failed: %s", exc)
            return False

    def set_autotune(self, enabled: bool) -> bool:
        try:
            self._client.set_heater_autotune(
                self.index, bool(enabled), float(self.autotune_target_temp)
            )
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_autotune failed: %s", exc)
            return False
