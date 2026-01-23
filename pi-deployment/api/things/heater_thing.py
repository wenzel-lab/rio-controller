"""Heater controller Thing for LabThings/WoT."""

import logging
from typing import TYPE_CHECKING, List

import labthings_fastapi as lt

# Handle Thing import with fallback
Thing = None
try:
    Thing = lt.Thing
except AttributeError:
    # Try alternate import path
    try:
        from labthings_fastapi.thing import Thing
    except (ImportError, AttributeError):
        # Fallback - create a simple base class
        class Thing:
            """Fallback Thing base class for when labthings_fastapi.Thing is unavailable."""
            def __init__(self, thing_server_interface=None):
                self.thing_server_interface = thing_server_interface

# Handle decorators with fallback
property_decorator = None
action_decorator = None
try:
    property_decorator = lt.property
    action_decorator = lt.action
except AttributeError:
    # Fallback decorators that do nothing
    def property_decorator(func):
        return func
    
    def action_decorator(func):
        return func

# Handle InvocationError import with fallback
InvocationError = None
try:
    from labthings_fastapi.exceptions import InvocationError
except (ImportError, AttributeError):
    # Fallback if labthings_fastapi doesn't have exceptions module
    InvocationError = Exception

from api.schemas import HeaterState, HeaterStateItem

if TYPE_CHECKING:
    from controllers.heater_web import heater_web

logger = logging.getLogger(__name__)


class HeaterThing(Thing):
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
        super().__init__(thing_server_interface)
        self._heaters = heaters

    @property_decorator
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

    @action_decorator
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

    @action_decorator
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

    @action_decorator
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
