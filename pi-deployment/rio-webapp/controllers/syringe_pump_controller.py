"""
Syringe pump web controller for handling WebSocket events.

Handles WebSocket commands and forwards them to the device syringe pump controller.
"""

import logging
from typing import Dict, Any

from flask_socketio import SocketIO

logger = logging.getLogger(__name__)


class SyringePumpWebController:
    """WebSocket controller for syringe pump operations."""

    def __init__(self, pump, socketio: SocketIO):
        """
        Args:
            pump: SyringePumpController device instance
            socketio: Flask-SocketIO instance
        """
        self.pump = pump
        self.socketio = socketio
        self._register_handlers()

    def _register_handlers(self) -> None:
        @self.socketio.on("pump")
        def on_pump(data: Dict[str, Any]) -> None:
            self.handle_pump_command(data)

    def _emit_state(self) -> None:
        try:
            state = self.pump.get_all_states()
            self.socketio.emit("pumps", state)
        except Exception as exc:
            logger.warning("Failed to emit pump state: %s", exc)

    def handle_pump_command(self, data: Dict[str, Any]) -> None:
        try:
            cmd = data.get("cmd")
            params = data.get("parameters", {})
            pump_id = params.get("pump")

            if cmd == "get_state":
                self._emit_state()
                return

            if pump_id is None:
                logger.error("Pump command missing pump id")
                return

            if cmd == "set_flow":
                self.pump.set_flow(pump_id, float(params.get("flow", 0.0)))
            elif cmd == "set_diameter":
                self.pump.set_diameter(pump_id, float(params.get("diameter", 0.0)))
            elif cmd == "set_direction":
                self.pump.set_direction(pump_id, params.get("direction", "infuse"))
            elif cmd == "set_state":
                self.pump.set_state(pump_id, params.get("state", False))
            elif cmd == "set_unit":
                self.pump.set_unit(pump_id, params.get("unit", "UL/HR"))
            elif cmd == "set_gearbox":
                self.pump.set_gearbox(pump_id, params.get("gearbox", "1:1"))
            elif cmd == "set_microstep":
                self.pump.set_microstep(pump_id, params.get("microstep", "1/16"))
            elif cmd == "set_threadrod":
                self.pump.set_threadrod(pump_id, params.get("threadrod", "1-START"))
            elif cmd == "set_enable":
                self.pump.set_enable(pump_id, bool(params.get("enabled", True)))
            else:
                logger.warning("Unknown pump command: %s", cmd)
                return

            self._emit_state()
        except Exception as exc:
            logger.error("Pump command failed: %s", exc)
