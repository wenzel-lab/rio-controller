"""Heater controller Thing for LabThings/WoT."""

import logging
from typing import TYPE_CHECKING, List

import labthings_fastapi as lt
from labthings_fastapi import decorators as lt_decorators

lt_action = getattr(lt_decorators, "action", None) or lt_decorators.thing_action
lt_property = getattr(lt_decorators, "property", None) or lt_decorators.thing_property
from labthings_fastapi import thing as lt_thing
try:
    from labthings_fastapi.exceptions import InvocationError
except ModuleNotFoundError:  # pragma: no cover - older labthings versions
    class InvocationError(RuntimeError):
        """Fallback invocation error for older labthings-fastapi versions."""

from api.schemas import HeaterState, HeaterStateItem

if TYPE_CHECKING:
    from controllers.heater_web import heater_web

logger = logging.getLogger(__name__)


class HeaterThing(lt_thing.Thing):
    """Heater controller Thing.

    Exposes heater control (temperature, PID, stirrer) as WoT-compliant properties and actions.
    """

    title = "Heater Controller"

    def __init__(self, heaters: List["heater_web"], thing_server_interface=None):
        """Initialize HeaterThing with heater controllers.

        Args:
            heaters: List of heater_web controller instances
            thing_server_interface: LabThings server interface (provided by ThingServer)
        """
        try:
            super().__init__(thing_server_interface)
        except TypeError:
            # LabThings 0.0.6 Thing has no __init__ params
            super().__init__()
        self._heaters = heaters

    @lt_property
    def state(self) -> HeaterState:
        """Get current heater state for all heaters.

        Returns:
            HeaterState with temperature, PID, and stirrer status
        """
        if self._heaters is None:
            raise RuntimeError("Heaters unavailable")

        items: List[HeaterStateItem] = []
        for h in self._heaters:
            h.update()
            items.append(
                HeaterStateItem(
                    temp_c_actual=h.temp_c_actual,
                    temp_c_target=h.temp_c_target,
                    pid_enabled=h.pid_enabled,
                    stir_enabled=h.stir_enabled,
                    autotuning=h.autotuning,
                    status_text=h.status_text,
                )
            )
        return HeaterState(heaters=items)

    @lt_action
    def set_temp(self, index: int, temp_c: float) -> dict:
        """Set target temperature for a heater.

        Args:
            index: Heater index (0-3)
            temp_c: Target temperature in Celsius

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If heaters unavailable or invalid index
        """
        if self._heaters is None:
            raise InvocationError("Heaters unavailable")
        if index < 0 or index >= len(self._heaters):
            raise InvocationError(
                f"Invalid heater index: {index} (must be 0-{len(self._heaters)-1})"
            )

        self._heaters[index].set_temp(temp_c)
        return {"ok": True}

    @lt_action
    def set_pid(self, index: int, enabled: bool) -> dict:
        """Enable or disable PID control for a heater.

        Args:
            index: Heater index (0-3)
            enabled: True to enable PID, False to disable

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If heaters unavailable or invalid index
        """
        if self._heaters is None:
            raise InvocationError("Heaters unavailable")
        if index < 0 or index >= len(self._heaters):
            raise InvocationError(
                f"Invalid heater index: {index} (must be 0-{len(self._heaters)-1})"
            )

        self._heaters[index].set_pid_running(1 if enabled else 0)
        self._heaters[index].pid_enabled = enabled
        return {"ok": True}

    @lt_action
    def set_stir(self, index: int, enabled: bool) -> dict:
        """Enable or disable stirrer for a heater.

        Args:
            index: Heater index (0-3)
            enabled: True to enable stirrer, False to disable

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If heaters unavailable or invalid index
        """
        if self._heaters is None:
            raise InvocationError("Heaters unavailable")
        if index < 0 or index >= len(self._heaters):
            raise InvocationError(
                f"Invalid heater index: {index} (must be 0-{len(self._heaters)-1})"
            )

        self._heaters[index].set_stir_running(1 if enabled else 0)
        self._heaters[index].stir_enabled = enabled
        return {"ok": True}
