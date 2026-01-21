"""Syringe pump controller (wraps USB serial driver or simulation)."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from config import PUMP_BAUDRATE, PUMP_PORT, PUMP_TIMEOUT_S, PUMP_WRITE_TIMEOUT_S
from drivers.syringe_pump_serial import SerialSyringePump, find_pump_port

logger = logging.getLogger(__name__)

PUMP_IDS = ["A", "B", "C", "D"]

# Global instance to prevent multiple processes from locking the COM port
_GLOBAL_SERIAL_PUMP: Optional[SerialSyringePump] = None


class SyringePumpController:
    """Controller wrapper around the syringe pump driver."""

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = PUMP_BAUDRATE,
        timeout_s: float = PUMP_TIMEOUT_S,
        write_timeout_s: float = PUMP_WRITE_TIMEOUT_S,
        simulation: Optional[bool] = None,
        backend: Optional[Any] = None,
    ):
        self._simulation = (
            simulation
            if simulation is not None
            else os.getenv("RIO_SIMULATION", "false").lower() == "true"
        )
        self._port = port or PUMP_PORT
        self._baudrate = baudrate
        self._timeout_s = timeout_s
        self._write_timeout_s = write_timeout_s
        self._backend_override = backend

        # Initialize or retrieve the existing backend
        self._pump = self._init_backend()

    def _init_backend(self):
        """Initializes the serial connection or reuses an existing one."""
        global _GLOBAL_SERIAL_PUMP

        if self._backend_override is not None:
            return self._backend_override

        # --- MODE A: SIMULATION ---
        if self._simulation:
            try:
                from simulation.pump_simulated import SimulatedPump

                logger.info("SyringePumpController: Initializing SIMULATED backend")
                return SimulatedPump()
            except ImportError:
                logger.error("Simulation module not found! Falling back to hardware check.")
                self._simulation = False

        # --- MODE B: REAL HARDWARE ---

        # 1. Check if the hardware is already connected
        if _GLOBAL_SERIAL_PUMP is not None:
            return _GLOBAL_SERIAL_PUMP

        # 2. Port Discovery
        if not self._port or self._port.lower() == "none":
            self._port = find_pump_port()

        if not self._port:
            raise RuntimeError(
                "Syringe pump controller enabled but no serial port found. "
                "Please set RIO_PUMP_PORT (e.g., COM5 or /dev/ttyUSB0)."
            )

        logger.info("SyringePumpController: Initializing HARDWARE backend on %s", self._port)

        # 3. Create the Serial Instance
        instance = SerialSyringePump(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout_s,
            write_timeout=self._write_timeout_s,
        )
        _GLOBAL_SERIAL_PUMP = instance
        return instance

    def close(self) -> None:
        """Closes the serial connection."""
        if hasattr(self._pump, "close"):
            try:
                self._pump.close()
            except Exception as exc:
                logger.warning("SyringePumpController close failed: %s", exc)

    # -------------------------
    # Validation Helpers
    # -------------------------
    def _validate_pump(self, pump: str) -> str:
        pump = pump.upper()
        if pump not in PUMP_IDS:
            raise ValueError(f"Invalid pump '{pump}' (expected A-D)")
        return pump

    def _normalize_direction(self, direction: Any) -> str:
        if isinstance(direction, (int, float)):
            return "INFUSE" if direction >= 0 else "WITHDRAW"
        value = str(direction).strip().upper()
        if value in ("INFUSE", "IN", "FORWARD", "1"):
            return "INFUSE"
        if value in ("WITHDRAW", "RETRACT", "OUT", "-1"):
            return "WITHDRAW"
        raise ValueError(f"Invalid direction '{direction}' (use INFUSE/WITHDRAW)")

    def _normalize_state(self, state: Any) -> str:
        if isinstance(state, bool):
            return "RUN" if state else "STOP"
        value = str(state).strip().upper()
        if value in ("RUN", "START", "ON", "1", "TRUE"):
            return "RUN"
        if value in ("STOP", "OFF", "0", "FALSE"):
            return "STOP"
        raise ValueError(f"Invalid state '{state}' (use RUN/STOP)")

    # -------------------------
    # API Methods
    # -------------------------
    def get_state(self, pump: str) -> Dict[str, Any]:
        pump = self._validate_pump(pump)
        status = self._pump.get_pump_status(pump)
        data = self._pump.parse_status(status)
        return {
            "pump": pump,
            "flow": float(data.get("FLOW", 0.0)) if "FLOW" in data else None,
            "diameter": float(data.get("DIAMETER", 0.0)) if "DIAMETER" in data else None,
            "direction": 1 if data.get("DIRECTION", "INFUSE").upper() == "INFUSE" else -1,
            "state": data.get("STATE", "STOP").upper() == "RUN",
            "unit": data.get("UNIT"),
            "gearbox": data.get("GEARBOX"),
            "microstep": data.get("MICROSTEP"),
            "threadrod": data.get("ROD"),
            "enabled": data.get("ENABLE", "OFF").upper() == "ON",
        }

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        return {pump: self.get_state(pump) for pump in PUMP_IDS}

    def set_flow(self, pump: str, flow: float) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_flow(pump, flow)
        return True

    def set_diameter(self, pump: str, diameter: float) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_diameter(pump, diameter)
        return True

    def set_direction(self, pump: str, direction: Any) -> bool:
        pump = self._validate_pump(pump)
        direction_value = self._normalize_direction(direction)
        self._pump.set_direction(pump, direction_value)
        return True

    def set_state(self, pump: str, state: Any) -> bool:
        pump = self._validate_pump(pump)
        state_value = self._normalize_state(state)
        self._pump.set_state(pump, state_value)
        return True

    def set_unit(self, pump: str, unit: str) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_unit(pump, unit)
        return True

    def set_gearbox(self, pump: str, gearbox: str) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_gearbox(pump, gearbox)
        return True

    def set_microstep(self, pump: str, microstep: str) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_microstep(pump, microstep)
        return True

    def set_threadrod(self, pump: str, threadrod: str) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_threadrod(pump, threadrod)
        return True

    def set_enable(self, pump: str, enabled: bool) -> bool:
        pump = self._validate_pump(pump)
        self._pump.set_enable(pump, enabled)
        return True
