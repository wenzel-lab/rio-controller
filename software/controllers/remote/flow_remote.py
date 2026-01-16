"""Remote flow controller adapter (API-backed)."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import List

from api.client import RioClient, RioAPIError
from config import CONTROL_MODE_FIRMWARE_TO_UI, CONTROL_MODE_UI_TO_FIRMWARE, FLOW_CTRL_MODE_STR

logger = logging.getLogger(__name__)


class RemoteFlow:
    """API-backed adapter that mimics FlowWeb for the Flask UI."""

    CTRL_MODE_STR = FLOW_CTRL_MODE_STR

    def __init__(self, client: RioClient) -> None:
        self._client = client
        self.flow = SimpleNamespace(NUM_CONTROLLERS=0)
        self.status_text: List[str] = []
        self.pressure_mbar_text: List[str] = []
        self.pressure_mbar_targets: List[float] = []
        self.flow_ul_hr_text: List[str] = []
        self.flow_ul_hr_targets: List[float] = []
        self.control_modes: List[int] = []
        self.control_modes_text: List[str] = []
        self.flow_pi_consts: List[List[int]] = []
        self.enabled = True
        self.connected = False
        self.reload = False
        self.update()

    def _set_channel_count(self, count: int) -> None:
        self.flow.NUM_CONTROLLERS = count
        if not self.status_text or len(self.status_text) != count:
            self.status_text = ["Init"] * count
            self.pressure_mbar_text = [""] * count
            self.pressure_mbar_targets = [0.0] * count
            self.flow_ul_hr_text = [""] * count
            self.flow_ul_hr_targets = [0.0] * count
            self.control_modes = [0] * count
            self.control_modes_text = [""] * count
            self.flow_pi_consts = [[0, 0] for _ in range(count)]

    def update(self) -> None:
        """Fetch flow state from API and update cached fields."""
        try:
            state = self._client.get_flow_state()
            pressure_targets = state.get("pressure_targets_mbar", [])
            flow_targets = state.get("flow_targets_ul_hr", [])
            pressure_actuals = state.get("pressure_actuals_mbar", [])
            flow_actuals = state.get("flow_actuals_ul_hr", [])
            control_modes_ui = state.get("control_modes_ui", [])
            control_modes_text = state.get("control_modes_text", [])

            channel_count = max(
                len(pressure_targets),
                len(flow_targets),
                len(control_modes_ui),
                len(pressure_actuals),
                len(flow_actuals),
            )
            if channel_count == 0:
                channel_count = 4

            self._set_channel_count(channel_count)
            self.pressure_mbar_targets = list(pressure_targets) + [0.0] * (
                channel_count - len(pressure_targets)
            )
            self.flow_ul_hr_targets = list(flow_targets) + [0.0] * (
                channel_count - len(flow_targets)
            )

            self.control_modes = [
                CONTROL_MODE_UI_TO_FIRMWARE.get(mode, 0) for mode in control_modes_ui
            ] + [0] * (channel_count - len(control_modes_ui))
            self.control_modes_text = list(control_modes_text) + [""] * (
                channel_count - len(control_modes_text)
            )

            for i in range(channel_count):
                target_p = self.pressure_mbar_targets[i]
                actual_p = pressure_actuals[i] if i < len(pressure_actuals) else 0.0
                target_f = self.flow_ul_hr_targets[i]
                actual_f = flow_actuals[i] if i < len(flow_actuals) else 0.0
                self.pressure_mbar_text[i] = f"{round(actual_p, 2)} / {round(target_p, 2)}"
                self.flow_ul_hr_text[i] = f"{round(actual_f, 2)} / {round(target_f, 2)}"

            self.status_text = ["Connected"] * channel_count
            self.connected = True
        except RioAPIError as exc:
            logger.warning("Remote flow update failed: %s", exc)
            if self.flow.NUM_CONTROLLERS:
                self.status_text = ["Offline"] * self.flow.NUM_CONTROLLERS
            self.connected = False

    def set_pressure(self, index: int, pressure_mbar: float) -> bool:
        try:
            self._client.set_pressure(index, pressure_mbar)
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_pressure failed: %s", exc)
            return False

    def set_flow(self, index: int, flow_ul_hr: float) -> bool:
        try:
            self._client.set_flow(index, flow_ul_hr)
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_flow failed: %s", exc)
            return False

    def set_control_mode(self, index: int, firmware_mode: int) -> bool:
        try:
            ui_mode = CONTROL_MODE_FIRMWARE_TO_UI.get(firmware_mode, 0)
            self._client.set_flow_mode(index, ui_mode)
            return True
        except RioAPIError as exc:
            logger.warning("Remote set_control_mode failed: %s", exc)
            return False

    def set_flow_pi_consts(self, index: int, pi_consts: List[int]) -> bool:
        try:
            p = int(pi_consts[0]) if len(pi_consts) > 0 else 0
            i = int(pi_consts[1]) if len(pi_consts) > 1 else 0
            self._client.set_flow_pi_consts(index, p, i)
            return True
        except (RioAPIError, ValueError, TypeError) as exc:
            logger.warning("Remote set_flow_pi_consts failed: %s", exc)
            return False
