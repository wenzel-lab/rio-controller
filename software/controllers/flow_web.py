"""
Flow control web interface module.

This module provides the FlowWeb class which acts as a bridge between the web
interface and the low-level flow controller hardware. It handles control mode
mapping between UI and firmware, and provides a clean interface for the web app.

Classes:
    FlowWeb: Web interface wrapper for flow controller
"""

import logging
import sys
import os
from typing import List, cast, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.flow import PiFlow  # noqa: E402

# Import configuration constants
try:
    # Config is now at software/ level (same level as controllers/)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import (
        FLOW_REPLY_PAUSE_S,
        FLOW_NUM_CONTROLLERS,
        CONTROL_MODE_FIRMWARE_TO_UI,
        CONTROL_MODE_UI_TO_FIRMWARE,
    )
except ImportError:
    # Fallback values if config module not available
    FLOW_REPLY_PAUSE_S = 0.1
    FLOW_NUM_CONTROLLERS = 4
    CONTROL_MODE_FIRMWARE_TO_UI = {0: 0, 1: 1, 2: 0, 3: 2}
    CONTROL_MODE_UI_TO_FIRMWARE = {0: 0, 1: 1, 2: 3}

# Configure logging
logger = logging.getLogger(__name__)


class FlowWeb:
    """
    Web interface wrapper for flow controller.

    This class provides a high-level interface for controlling flow and pressure
    through the web interface. It handles mapping between UI control modes and
    firmware control modes, and manages state synchronization.

    Attributes:
        flow: Low-level PiFlow instance for hardware communication
        status_text: List of status strings for each controller
        pressure_mbar_text: List of formatted pressure strings
        pressure_mbar_targets: List of target pressure values (mbar)
        flow_ul_hr_text: List of formatted flow strings
        flow_ul_hr_targets: List of target flow values (ul/hr)
        control_modes: List of firmware control mode values
        control_modes_text: List of UI display strings for control modes
        flow_pi_consts: List of PI control constants [P, I] for each controller
        enabled: Whether the flow controller is enabled
        connected: Whether communication with hardware is active
        reload: Flag indicating state reload is needed
    """

    # Control mode display strings (UI indices)
    CTRL_MODE_STR = ["Off", "Set Pressure", "Flow Closed Loop"]

    # Status strings
    PRESS_STATUS_STR = ["Unconfigured", "Idle", "Active", "Error"]

    FLOW_STATUS_STR = ["Unconfigured", "Idle", "Active", "Error"]

    def __init__(self, port: int) -> None:
        """
        Initialize the FlowWeb interface.

        Args:
            port: GPIO port number for SPI device selection
        """
        logger.info(f"Initializing FlowWeb on port {port}")
        self.flow = PiFlow(port, FLOW_REPLY_PAUSE_S)

        # Initialize state arrays for all controllers
        num_controllers = self.flow.NUM_CONTROLLERS
        self.status_text: List[str] = ["Init"] * num_controllers
        self.pressure_mbar_text: List[str] = [""] * num_controllers
        self.pressure_mbar_targets: List[float] = [0.0] * num_controllers
        self.flow_ul_hr_text: List[str] = [""] * num_controllers
        self.flow_ul_hr_targets: List[float] = [0.0] * num_controllers
        self.control_modes: List[int] = [0] * num_controllers
        self.control_modes_text: List[str] = [""] * num_controllers
        self.flow_pi_consts: List[List[int]] = [[0, 0] for _ in range(num_controllers)]

        # Initialize hardware connection
        try:
            valid, device_id, id_valid = self.flow.get_id()
            logger.info(f"Flow controller ID check: valid={id_valid}, ID={device_id}")
            self.enabled = valid and id_valid
            self.connected = self.enabled
        except Exception as e:
            logger.error(f"Error initializing flow controller: {e}")
            self.enabled = False
            self.connected = False

        self.reload = False

        # Load initial state from hardware
        if self.enabled:
            try:
                self.get_pressure_targets()
                self.get_flow_targets()
                self.get_control_modes()
                self.get_flow_pi_consts()
            except Exception as e:
                logger.error(f"Error loading initial flow controller state: {e}")

    def get_pressure_targets(self) -> None:
        """
        Retrieve pressure targets from hardware and update internal state.
        """
        try:
            valid, pressures_mbar_targets = self.flow.get_pressure_target()
            if valid:
                self.pressure_mbar_targets = pressures_mbar_targets
            else:
                logger.warning("Failed to get pressure targets from hardware")
        except Exception as e:
            logger.error(f"Error getting pressure targets: {e}")

    def get_flow_targets(self) -> List[int]:
        """
        Retrieve flow targets from hardware and update internal state.

        Returns:
            List of flow targets in ul/hr
        """
        try:
            valid, flows_ul_hr_targets = self.flow.get_flow_target()
            if valid:
                self.flow_ul_hr_targets = flows_ul_hr_targets
                return cast(List[int], flows_ul_hr_targets)
            else:
                logger.warning("Failed to get flow targets from hardware")
                return []
        except Exception as e:
            logger.error(f"Error getting flow targets: {e}")
            return []

    def get_control_modes(self) -> List[int]:
        """
        Retrieve control modes from hardware and map to UI display strings.

        Maps firmware control modes to UI indices, hiding the deprecated
        "Pressure Closed Loop" mode (firmware mode 2).

        Returns:
            List of control mode integers (firmware format)
        """
        try:
            valid, control_modes = self.flow.get_control_modes()
            if not valid:
                logger.warning("Failed to get control modes from hardware")
                return []  # Return empty list instead of None

            self.control_modes = control_modes
            # Map firmware modes to UI display strings
            # Firmware: 0=Off, 1=Pressure Open Loop, 2=Pressure Closed Loop (hidden), 3=Flow Closed Loop
            # UI: 0=Off, 1=Set Pressure, 2=Flow Closed Loop
            self.control_modes_text = []
            for firmware_mode in control_modes:
                ui_index = CONTROL_MODE_FIRMWARE_TO_UI.get(firmware_mode, 0)
                if ui_index < len(self.CTRL_MODE_STR):
                    self.control_modes_text.append(self.CTRL_MODE_STR[ui_index])
                else:
                    logger.warning(f"Invalid UI index {ui_index} for firmware mode {firmware_mode}")
                    self.control_modes_text.append(self.CTRL_MODE_STR[0])  # Default to "Off"
            return cast(List[int], control_modes)
        except Exception as e:
            logger.error(f"Error getting control modes: {e}")
            return []

    def get_flow_pi_consts(self) -> None:
        """
        Retrieve flow PI control constants from hardware.

        Extracts only P and I terms from the PID constants (D is always 0 for PI control).
        """
        try:
            valid, flow_pid_consts = self.flow.get_flow_pid_consts()
            if valid:
                # Extract only P and I, set D=0 for PI control
                self.flow_pi_consts = [
                    [pid_consts[0], pid_consts[1]] for pid_consts in flow_pid_consts
                ]
            else:
                logger.warning("Failed to get flow PI constants from hardware")
        except Exception as e:
            logger.error(f"Error getting flow PI constants: {e}")

    def set_pressure(self, index: int, pressure_mbar: float) -> bool:
        """
        Set pressure target for a specific controller.

        Args:
            index: Controller index (0-3)
            pressure_mbar: Target pressure in millibars

        Returns:
            True if successful, False otherwise
        """
        try:
            if not 0 <= index < self.flow.NUM_CONTROLLERS:
                logger.error(f"Invalid controller index: {index}")
                return False

            pressure = int(pressure_mbar)
            valid = self.flow.set_pressure([index], [pressure])
            if valid:
                self.get_pressure_targets()
                logger.debug(f"Pressure set for controller {index}: {pressure} mbar")
            else:
                logger.warning(f"Failed to set pressure for controller {index}")
            return cast(bool, valid)
        except (ValueError, TypeError) as e:
            logger.error(f"Error setting pressure: {e}")
            return False

    def set_flow(self, index: int, flow_ul_hr: float) -> bool:
        """
        Set flow target for a specific controller.

        Args:
            index: Controller index (0-3)
            flow_ul_hr: Target flow in microliters per hour

        Returns:
            True if successful, False otherwise
        """
        try:
            if not 0 <= index < self.flow.NUM_CONTROLLERS:
                logger.error(f"Invalid controller index: {index}")
                return False

            flow = int(flow_ul_hr)
            valid = self.flow.set_flow([index], [flow])
            if valid:
                self.get_flow_targets()
                logger.debug(f"Flow set for controller {index}: {flow} ul/hr")
            else:
                logger.warning(f"Failed to set flow for controller {index}")
            return cast(bool, valid)
        except (ValueError, TypeError) as e:
            logger.error(f"Error setting flow: {e}")
            return False

    def set_control_mode(self, index: int, control_mode: int) -> bool:
        """
        Set control mode for a specific controller.

        Maps UI control mode index to firmware control mode and sets it.

        Args:
            index: Controller index (0-3)
            control_mode: UI control mode index (0=Off, 1=Set Pressure, 2=Flow Closed Loop)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not 0 <= index < self.flow.NUM_CONTROLLERS:
                logger.error(f"Invalid controller index: {index}")
                return False

            # Map UI mode index to firmware mode
            firmware_mode = CONTROL_MODE_UI_TO_FIRMWARE.get(control_mode)
            if firmware_mode is None:
                logger.error(f"Invalid control mode: {control_mode}")
                return False

            valid = self.flow.set_control_mode([index], [firmware_mode])
            if valid:
                self.get_control_modes()
                logger.debug(
                    f"Control mode set for controller {index}: "
                    f"UI={control_mode}, Firmware={firmware_mode}"
                )
            else:
                logger.warning(f"Failed to set control mode for controller {index}")
            return cast(bool, valid)
        except Exception as e:
            logger.error(f"Error setting control mode: {e}")
            return False

    def set_flow_pi_consts(self, index: int, pi_consts: List[int]) -> bool:
        """
        Set flow PI control constants for a specific controller.

        Converts PI constants [P, I] to PID format [P, I, 0] where D=0.

        Args:
            index: Controller index (0-3)
            pi_consts: List of [P, I] constants

        Returns:
            True if successful, False otherwise
        """
        try:
            if not 0 <= index < self.flow.NUM_CONTROLLERS:
                logger.error(f"Invalid controller index: {index}")
                return False

            if len(pi_consts) < 2:
                logger.error(f"Invalid PI constants: {pi_consts}")
                return False

            # Convert PI to PID format: [P, I] -> [P, I, 0] (D=0 for PI control)
            pid_consts = [pi_consts[0], pi_consts[1], 0]
            valid = self.flow.set_flow_pid_consts([index], [pid_consts])
            if valid:
                self.get_flow_pi_consts()
                logger.debug(
                    f"PI constants set for controller {index}: P={pi_consts[0]}, I={pi_consts[1]}"
                )
            else:
                logger.warning(f"Failed to set PI constants for controller {index}")
            return cast(bool, valid)
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Error setting flow PI constants: {e}")
            return False

    def update(self) -> None:
        """
        Update flow controller state from hardware.

        Reads current pressure and flow values from hardware, updates internal
        state, and handles connection status. If connection is restored,
        reloads all state from hardware.
        """
        if not self.enabled:
            self.status_text = ["Offline"] * self.flow.NUM_CONTROLLERS
            return

        try:
            valid, pressures_actual, flows_actual = self._read_hardware_values()
            self._handle_connection_restore(valid)
            self._update_status_text(valid)
            self._update_display_strings(pressures_actual, flows_actual)
        except Exception as e:
            logger.error(f"Error updating flow controller state: {e}")
            self.connected = False
            self.status_text = ["Error"] * self.flow.NUM_CONTROLLERS

    def _read_hardware_values(self) -> tuple[bool, List[float], List[float]]:
        """Read pressure and flow values from hardware."""
        valid = True
        pressures_actual: List[float] = []
        flows_actual: List[float] = []

        try:
            valid_pressure, pressures_actual = self.flow.get_pressure_actual()
            if not valid_pressure:
                logger.warning("Failed to get pressure actual values")
            valid = valid and valid_pressure
        except Exception as e:
            logger.error(f"Error reading pressure actual: {e}")
            valid = False

        try:
            valid_flow, flows_actual = self.flow.get_flow_actual()
            if not valid_flow:
                logger.warning("Failed to get flow actual values")
            valid = valid and valid_flow
        except Exception as e:
            logger.error(f"Error reading flow actual: {e}")
            valid = False

        return valid, pressures_actual, flows_actual

    def _handle_connection_restore(self, valid: bool) -> None:
        """Handle connection restore by reloading state."""
        if valid and not self.connected:
            logger.info("Flow controller connection restored, reloading state")
            self.get_pressure_targets()
            self.get_flow_targets()
            self.get_control_modes()
            self.get_flow_pi_consts()
            self.reload = True
        self.connected = valid

    def _update_status_text(self, valid: bool) -> None:
        """Update status text based on connection state."""
        if not valid:
            self.status_text = ["Connection Error"] * self.flow.NUM_CONTROLLERS
        else:
            self.status_text = ["Connected"] * self.flow.NUM_CONTROLLERS

    def _update_display_strings(
        self, pressures_actual: List[float], flows_actual: List[float]
    ) -> None:
        """Update formatted display strings."""
        try:
            if pressures_actual and len(pressures_actual) == self.flow.NUM_CONTROLLERS:
                self.pressure_mbar_text = [
                    f"{round(pressures_actual[i], 2)} / {round(self.pressure_mbar_targets[i], 2)}"
                    for i in range(self.flow.NUM_CONTROLLERS)
                ]
            if flows_actual and len(flows_actual) == self.flow.NUM_CONTROLLERS:
                self.flow_ul_hr_text = [
                    f"{round(flows_actual[i], 2)} / {round(self.flow_ul_hr_targets[i], 2)}"
                    for i in range(self.flow.NUM_CONTROLLERS)
                ]
        except (IndexError, TypeError) as e:
            logger.error(f"Error formatting pressure/flow text: {e}")
