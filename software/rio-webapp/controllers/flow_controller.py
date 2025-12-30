"""
Flow controller for handling flow control WebSocket events.

This module handles all flow-related WebSocket commands, keeping the
controller logic separate from the view and model layers.

Classes:
    FlowController: Handles flow control WebSocket events
"""

import logging
import sys
import os
from typing import Dict, Any
from flask_socketio import SocketIO

# Add parent directories to path for imports (software/ level)
software_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if software_root not in sys.path:
    sys.path.insert(0, software_root)
from controllers.flow_web import FlowWeb  # noqa: E402
from view_model import ViewModel  # noqa: E402
from config import CONTROL_MODE_UI_TO_FIRMWARE  # noqa: E402

# Configure logging
logger = logging.getLogger(__name__)


class FlowController:
    """
    Controller for flow control operations.

    Handles WebSocket events related to flow and pressure control.
    Keeps controller logic separate from view and model.
    """

    def __init__(self, flow: FlowWeb, socketio: SocketIO):
        """
        Initialize flow controller.

        Args:
            flow: FlowWeb model instance
            socketio: Flask-SocketIO instance for WebSocket communication
        """
        self.flow = flow
        self.socketio = socketio
        self.view_model = ViewModel()
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register WebSocket event handlers."""

        @self.socketio.on("flow")
        def on_flow(data: Dict[str, Any]) -> None:
            self.handle_flow_command(data)

    def handle_flow_command(self, data: Dict[str, Any]) -> None:
        """
        Handle flow control command.

        Args:
            data: Dictionary containing 'cmd' and 'parameters' keys
        """
        try:
            cmd = data.get("cmd")
            params = data.get("parameters", {})
            index = params.get("index", -1)

            if index < 0 or index >= len(self.flow.control_modes):
                logger.error(f"Invalid controller index: {index}")
                return

            valid = False

            if cmd == "pressure_mbar_target":
                pressure_mbar_target = params.get("pressure_mbar_target", 0.0)
                valid = self.flow.set_pressure(index, pressure_mbar_target)
                logger.debug(f"Set pressure for channel {index}: {pressure_mbar_target} mbar")

            elif cmd == "flow_ul_hr_target":
                flow_ul_hr_target = params.get("flow_ul_hr_target", 0.0)
                valid = self.flow.set_flow(index, flow_ul_hr_target)
                logger.debug(f"Set flow for channel {index}: {flow_ul_hr_target} ul/hr")

            elif cmd == "control_mode":
                ui_control_mode = int(params.get("control_mode", 0))
                firmware_mode = CONTROL_MODE_UI_TO_FIRMWARE.get(ui_control_mode, 0)
                valid = self.flow.set_control_mode(index, firmware_mode)
                logger.debug(
                    f"Set control mode for channel {index}: UI={ui_control_mode}, Firmware={firmware_mode}"
                )

            elif cmd == "flow_pi_consts":
                pi_p = int(params.get("p", 0))
                pi_i = int(params.get("i", 0))
                pi_consts = [pi_p, pi_i]
                valid = self.flow.set_flow_pi_consts(index, pi_consts)
                logger.debug(f"Set PI constants for channel {index}: P={pi_p}, I={pi_i}")
            else:
                logger.warning(f"Unknown flow command: {cmd}")
                return

            if not valid:
                logger.warning(f"Flow command '{cmd}' failed for channel {index}")

            # Update model and emit formatted data
            self.flow.update()
            flows_data = self.view_model.format_flow_data(self.flow)
            self.socketio.emit("flows", flows_data)

        except (KeyError, ValueError, TypeError, AttributeError) as e:
            logger.error(f"Error handling flow command: {e}")
            logger.debug(f"Command data: {data}")
