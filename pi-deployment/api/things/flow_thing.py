"""Flow and pressure controller Thing for LabThings/WoT."""

import logging
from typing import TYPE_CHECKING

import labthings_fastapi as lt
from labthings_fastapi.exceptions import InvocationError

from api.schemas import FlowState
from config import CONTROL_MODE_UI_TO_FIRMWARE, CONTROL_MODE_FIRMWARE_TO_UI

if TYPE_CHECKING:
    from controllers.flow_web import FlowWeb

logger = logging.getLogger(__name__)


class FlowThing(lt.Thing):
    """Flow and pressure controller Thing.

    Exposes flow and pressure control as WoT-compliant properties and actions.
    """

    title = "Flow and Pressure Controller"

    def __init__(self, flow_controller: "FlowWeb", thing_server_interface=None):
        """Initialize FlowThing with a FlowWeb controller.

        Args:
            flow_controller: FlowWeb controller instance
            thing_server_interface: LabThings server interface (provided by ThingServer)
        """
        super().__init__(thing_server_interface)
        self._flow = flow_controller

    @lt.property
    def state(self) -> FlowState:
        """Get current flow and pressure state for all channels.

        Returns:
            FlowState with targets, actuals, and control modes
        """
        if self._flow is None:
            raise RuntimeError("Flow controller unavailable")

        # Get all values at once (returns tuple: valid, list[float])
        ok_p, pressure_actuals = self._flow.flow.get_pressure_actual()
        if not ok_p:
            pressure_actuals = [0.0] * self._flow.flow.NUM_CONTROLLERS
        ok_f, flow_actuals = self._flow.flow.get_flow_actual()
        if not ok_f:
            flow_actuals = [0.0] * self._flow.flow.NUM_CONTROLLERS

        # Update cached targets/modes
        self._flow.get_pressure_targets()
        self._flow.get_flow_targets()
        self._flow.get_control_modes()

        return FlowState(
            pressure_targets_mbar=self._flow.pressure_mbar_targets,
            pressure_actuals_mbar=pressure_actuals,
            flow_targets_ul_hr=self._flow.flow_ul_hr_targets,
            flow_actuals_ul_hr=flow_actuals,
            control_modes_ui=[
                CONTROL_MODE_FIRMWARE_TO_UI.get(m, 0) for m in self._flow.control_modes
            ],
            control_modes_text=self._flow.control_modes_text,
        )

    @lt.action
    def set_pressure(self, index: int, pressure_mbar: float) -> dict:
        """Set pressure target for a channel.

        Args:
            index: Channel index (0-3)
            pressure_mbar: Target pressure in mbar

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If controller unavailable or set failed
        """
        if self._flow is None:
            raise InvocationError("Flow controller unavailable")
        if not (0 <= index <= 3):
            raise InvocationError(f"Invalid channel index: {index} (must be 0-3)")

        ok = self._flow.set_pressure(index, pressure_mbar)
        if not ok:
            raise InvocationError("Failed to set pressure")
        return {"ok": True}

    @lt.action
    def set_flow(self, index: int, flow_ul_hr: float) -> dict:
        """Set flow rate target for a channel.

        Args:
            index: Channel index (0-3)
            flow_ul_hr: Target flow rate in ul/hr

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If controller unavailable or set failed
        """
        if self._flow is None:
            raise InvocationError("Flow controller unavailable")
        if not (0 <= index <= 3):
            raise InvocationError(f"Invalid channel index: {index} (must be 0-3)")

        ok = self._flow.set_flow(index, flow_ul_hr)
        if not ok:
            raise InvocationError("Failed to set flow rate")
        return {"ok": True}

    @lt.action
    def set_mode(self, index: int, mode_ui: int) -> dict:
        """Set control mode for a channel.

        Args:
            index: Channel index (0-3)
            mode_ui: UI control mode (0=Off, 1=Set Pressure, 2=Flow Closed Loop)

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If controller unavailable or set failed
        """
        if self._flow is None:
            raise InvocationError("Flow controller unavailable")
        if not (0 <= index <= 3):
            raise InvocationError(f"Invalid channel index: {index} (must be 0-3)")

        firmware_mode = CONTROL_MODE_UI_TO_FIRMWARE.get(mode_ui, 0)
        ok = self._flow.set_control_mode(index, firmware_mode)
        if not ok:
            raise InvocationError("Failed to set control mode")
        return {"ok": True}

    @lt.action
    def set_pi_consts(self, index: int, p: int, i: int) -> dict:
        """Set PI control constants for a channel.

        Args:
            index: Channel index (0-3)
            p: Proportional constant
            i: Integral constant

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If controller unavailable or set failed
        """
        if self._flow is None:
            raise InvocationError("Flow controller unavailable")
        if not (0 <= index <= 3):
            raise InvocationError(f"Invalid channel index: {index} (must be 0-3)")
        if p < 0 or i < 0:
            raise InvocationError("PI constants must be non-negative")

        ok = self._flow.set_flow_pi_consts(index, [p, i])
        if not ok:
            raise InvocationError("Failed to set PI constants")
        return {"ok": True}
