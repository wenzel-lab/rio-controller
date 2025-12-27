"""
Heater controller for handling heater control WebSocket events.

This module handles all heater-related WebSocket commands, keeping the
controller logic separate from the view and model layers.

Classes:
    HeaterController: Handles heater control WebSocket events
"""

import logging
from typing import Dict, Any, List
from flask_socketio import SocketIO
from view_model import ViewModel

# Configure logging
logger = logging.getLogger(__name__)


class HeaterController:
    """
    Controller for heater control operations.

    Handles WebSocket events related to heater and temperature control.
    Keeps controller logic separate from view and model.
    """

    def __init__(self, heaters: List[Any], socketio: SocketIO):
        """
        Initialize heater controller.

        Args:
            heaters: List of heater_web model instances
            socketio: Flask-SocketIO instance for WebSocket communication
        """
        self.heaters = heaters
        self.socketio = socketio
        self.view_model = ViewModel()
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register WebSocket event handlers."""

        @self.socketio.on("heater")
        def on_heater(data: Dict[str, Any]) -> None:
            self.handle_heater_command(data)

    def handle_heater_command(self, data: Dict[str, Any]) -> None:
        """
        Handle heater control command.

        Args:
            data: Dictionary containing 'cmd' and 'parameters' keys
        """
        try:
            cmd = data.get("cmd")
            params = data.get("parameters", {})
            index = params.get("index", -1)

            if index < 0 or index >= len(self.heaters):
                logger.error(f"Invalid heater index: {index}")
                return

            heater = self.heaters[index]
            valid = False

            if cmd == "temp_c_target":
                temp_c_target = params.get("temp_c_target", 0.0)
                valid = heater.set_temp(temp_c_target)
                logger.debug(f"Set temperature for heater {index}: {temp_c_target}°C")

            elif cmd == "pid_enable":
                enabled = params.get("on", False)
                valid = heater.set_pid_running(enabled)
                logger.debug(f"Set PID enable for heater {index}: {enabled}")

            elif cmd == "power_limit_pc":
                power_limit_pc = params.get("power_limit_pc", 0)
                valid = heater.set_heat_power_limit_pc(power_limit_pc)
                logger.debug(f"Set power limit for heater {index}: {power_limit_pc}%")

            elif cmd == "autotune":
                enabled = params.get("on", False)
                temp = params.get("temp", 50.0)
                heater.autotune_target_temp = temp
                valid = heater.set_autotune(enabled)
                logger.debug(f"Set autotune for heater {index}: enabled={enabled}, temp={temp}°C")

            elif cmd == "stir":
                enabled = params.get("on", False)
                speed = params.get("speed", 0)
                heater.stir_target_speed = speed
                valid = heater.set_stir_running(enabled)
                logger.debug(f"Set stir for heater {index}: enabled={enabled}, speed={speed}")
            else:
                logger.warning(f"Unknown heater command: {cmd}")
                return

            if not valid:
                logger.warning(f"Heater command '{cmd}' failed for heater {index}")

            # Update model and emit formatted data
            heater.update()
            heaters_data = self.view_model.format_heater_data(self.heaters)
            self.socketio.emit("heaters", heaters_data)

        except (KeyError, ValueError, TypeError, AttributeError, IndexError) as e:
            logger.error(f"Error handling heater command: {e}")
            logger.debug(f"Command data: {data}")
