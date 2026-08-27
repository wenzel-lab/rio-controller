"""Remote strobe hardware adapter (API-backed) for hybrid Pi + host deployments.

CoolerMaster/UI keeps a local camera (e.g. Daheng) while strobe SPI stays on the Pi.
Replaces ``PiStrobeCam.strobe`` with this driver when ``strobe`` is in
``RIO_REMOTE_MODULES`` (or ``RIO_REMOTE_STROBE=1``).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from api.client import RioAPIError, RioClient

logger = logging.getLogger(__name__)


class RemoteStrobe:
    """Mimics ``drivers.strobe.PiStrobe`` via Rio API ``/api/control/strobe/*``."""

    def __init__(self, client: RioClient) -> None:
        self._client = client
        self._last_wait_ns = 0
        self._last_period_ns = 0
        self._last_trigger_mode = 0  # 0=software, 1=hardware

    def set_enable(self, enable: Any) -> bool:
        try:
            self._client.set_strobe_enable(bool(enable))
            return True
        except RioAPIError as exc:
            logger.error("Remote strobe set_enable(%s) failed: %s", enable, exc)
            return False

    def set_hold(self, hold: Any) -> bool:
        try:
            self._client.set_strobe_hold(bool(hold))
            return True
        except RioAPIError as exc:
            logger.error("Remote strobe set_hold(%s) failed: %s", hold, exc)
            return False

    def set_timing(self, wait_ns: int, period_ns: int) -> Tuple[bool, int, int]:
        try:
            self._client.set_strobe_timing(period_ns=int(period_ns), wait_ns=int(wait_ns))
            state = self._client.get_strobe_state()
            wait = int(state.get("wait_ns", wait_ns) or wait_ns)
            period = int(state.get("period_ns", period_ns) or period_ns)
            self._last_wait_ns = wait
            self._last_period_ns = period
            return True, wait, period
        except RioAPIError as exc:
            logger.error(
                "Remote strobe set_timing(wait=%s, period=%s) failed: %s",
                wait_ns,
                period_ns,
                exc,
            )
            return False, int(wait_ns), int(period_ns)

    def set_trigger_mode(self, hardware_trigger: Any) -> bool:
        try:
            hw = bool(hardware_trigger)
            self._client.set_strobe_trigger_mode(hw)
            self._last_trigger_mode = 1 if hw else 0
            return True
        except RioAPIError as exc:
            logger.error("Remote strobe set_trigger_mode(%s) failed: %s", hardware_trigger, exc)
            return False

    def get_cam_read_time(self) -> Tuple[bool, int]:
        try:
            state = self._client.get_strobe_state()
            us = int(state.get("cam_read_time_us", 0) or 0)
            return True, us
        except RioAPIError as exc:
            logger.debug("Remote strobe get_cam_read_time failed: %s", exc)
            return False, 0

    def get_state(self) -> Dict[str, Any]:
        try:
            state = dict(self._client.get_strobe_state())
            if state.get("trigger_mode") is not None:
                self._last_trigger_mode = int(state["trigger_mode"])
            return state
        except RioAPIError as exc:
            logger.warning("Remote strobe get_state failed: %s", exc)
            return {
                "hold": 0,
                "enable": 0,
                "wait_ns": self._last_wait_ns,
                "period_ns": self._last_period_ns,
                "framerate": 0,
                "cam_read_time_us": 0,
                "trigger_mode": self._last_trigger_mode,
            }
