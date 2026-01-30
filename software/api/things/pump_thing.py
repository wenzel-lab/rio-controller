"""Syringe pump controller Thing for LabThings/WoT."""

import logging
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


logger = logging.getLogger(__name__)


class PumpThing(lt_thing.Thing):
    """Syringe pump controller Thing."""

    title = "Syringe Pump Controller"

    def __init__(self, pump_controller=None, thing_server_interface=None):
        """Initialize PumpThing.

        Args:
            pump_controller: Pump controller instance
            thing_server_interface: LabThings server interface (provided by ThingServer)
        """
        try:
            super().__init__(thing_server_interface)
        except TypeError:
            # LabThings 0.0.6 Thing has no __init__ params
            super().__init__()
        self._pump = pump_controller

    @lt_property
    def state(self) -> dict:
        """Get current pump state.

        Returns:
            Dictionary of pump states keyed by pump id
        """
        if self._pump is None:
            raise RuntimeError("Pump controller unavailable")
        return {"pumps": self._pump.get_all_states()}

    @lt_action
    def set_flow(self, pump: str, flow: float) -> dict:
        """Set flow rate for a pump.

        Args:
            pump: Pump identifier (A, B, C, or D)
            flow: Flow rate

        Returns:
            {"ok": True} on success

        """
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_flow(pump, flow)
        if not ok:
            raise InvocationError("Failed to set flow")
        return {"ok": True}

    @lt_action
    def set_diameter(self, pump: str, diameter: float) -> dict:
        """Set syringe diameter for a pump.

        Args:
            pump: Pump identifier (A, B, C, or D)
            diameter: Syringe diameter

        Returns:
            {"ok": True} on success

        """
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_diameter(pump, diameter)
        if not ok:
            raise InvocationError("Failed to set diameter")
        return {"ok": True}

    @lt_action
    def set_direction(self, pump: str, direction: int) -> dict:
        """Set flow direction for a pump.

        Args:
            pump: Pump identifier (A, B, C, or D)
            direction: Flow direction ("infuse" or "withdraw")

        Returns:
            {"ok": True} on success

        """
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_direction(pump, direction)
        if not ok:
            raise InvocationError("Failed to set direction")
        return {"ok": True}

    @lt_action
    def set_state(self, pump: str, state: bool) -> dict:
        """Set pump state.

        Args:
            pump: Pump identifier (A, B, C, or D)
            state: Pump state ("run" or "stop")

        Returns:
            {"ok": True} on success

        """
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_state(pump, state)
        if not ok:
            raise InvocationError("Failed to set state")
        return {"ok": True}

    @lt_action
    def set_unit(self, pump: str, unit: str) -> dict:
        """Set pump flow unit."""
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_unit(pump, unit)
        if not ok:
            raise InvocationError("Failed to set unit")
        return {"ok": True}

    @lt_action
    def set_gearbox(self, pump: str, gearbox: str) -> dict:
        """Set pump gearbox configuration."""
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_gearbox(pump, gearbox)
        if not ok:
            raise InvocationError("Failed to set gearbox")
        return {"ok": True}

    @lt_action
    def set_microstep(self, pump: str, microstep: str) -> dict:
        """Set pump microstep configuration."""
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_microstep(pump, microstep)
        if not ok:
            raise InvocationError("Failed to set microstep")
        return {"ok": True}

    @lt_action
    def set_threadrod(self, pump: str, threadrod: str) -> dict:
        """Set pump threadrod configuration."""
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_threadrod(pump, threadrod)
        if not ok:
            raise InvocationError("Failed to set threadrod")
        return {"ok": True}

    @lt_action
    def set_enable(self, pump: str, enabled: bool) -> dict:
        """Enable or disable pump."""
        if self._pump is None:
            raise InvocationError("Pump controller unavailable")
        ok = self._pump.set_enable(pump, enabled)
        if not ok:
            raise InvocationError("Failed to set enable")
        return {"ok": True}
