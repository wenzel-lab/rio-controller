"""Syringe pump controller Thing for LabThings/WoT (placeholder)."""

import logging
from typing import TYPE_CHECKING

import labthings_fastapi as lt

logger = logging.getLogger(__name__)


class PumpThing(lt.Thing):
    """Syringe pump controller Thing (placeholder).

    This is a placeholder until the pump driver/controller is implemented.
    All actions will raise InvocationError with 501 Not Implemented.
    """

    title = "Syringe Pump Controller"

    def __init__(self, pump_controller=None, thing_server_interface=None):
        """Initialize PumpThing (placeholder).

        Args:
            pump_controller: Pump controller instance (currently None)
            thing_server_interface: LabThings server interface (provided by ThingServer)
        """
        super().__init__(thing_server_interface)
        self._pump = pump_controller

    @lt.property
    def state(self) -> dict:
        """Get current pump state (placeholder).

        Returns:
            Dictionary with pump state (placeholder)

        Raises:
            RuntimeError: Pump controller not implemented
        """
        raise RuntimeError("Pump controller not yet implemented")

    @lt.action
    def set_flow(self, pump: str, flow: float) -> dict:
        """Set flow rate for a pump (placeholder).

        Args:
            pump: Pump identifier (A, B, C, or D)
            flow: Flow rate

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: Pump controller not implemented
        """
        raise lt.InvocationError("Pump controller not yet implemented")

    @lt.action
    def set_diameter(self, pump: str, diameter: float) -> dict:
        """Set syringe diameter for a pump (placeholder).

        Args:
            pump: Pump identifier (A, B, C, or D)
            diameter: Syringe diameter

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: Pump controller not implemented
        """
        raise lt.InvocationError("Pump controller not yet implemented")

    @lt.action
    def set_direction(self, pump: str, direction: str) -> dict:
        """Set flow direction for a pump (placeholder).

        Args:
            pump: Pump identifier (A, B, C, or D)
            direction: Flow direction ("infuse" or "withdraw")

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: Pump controller not implemented
        """
        raise lt.InvocationError("Pump controller not yet implemented")

    @lt.action
    def set_state(self, pump: str, state: str) -> dict:
        """Set pump state (placeholder).

        Args:
            pump: Pump identifier (A, B, C, or D)
            state: Pump state ("run" or "stop")

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: Pump controller not implemented
        """
        raise lt.InvocationError("Pump controller not yet implemented")

