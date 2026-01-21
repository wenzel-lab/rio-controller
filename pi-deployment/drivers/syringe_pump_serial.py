"""USB-serial driver for the 3D-printed syringe pump controller (ESP32)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT_S = 1.0

T = TypeVar("T")


def find_pump_port() -> Optional[str]:
    """Best-effort port detection for the syringe pump controller."""
    try:
        import serial.tools.list_ports
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("pyserial not available for port discovery: %s", exc)
        return None

    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        desc = (port.description or "").upper()
        if "USB" in desc or "CH340" in desc or "CP210" in desc:
            return cast(str, port.device)
    return None


class SerialSyringePump:
    """Serial protocol driver (direct USB communication)."""

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT_S,
        write_timeout: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        try:
            import serial
        except ImportError as exc:
            raise ImportError("pyserial is required. Install with: pip install pyserial") from exc

        self._lock = threading.Lock()

        self._serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=write_timeout,
            dsrdtr=False,
            rtscts=False,
        )

        self._serial.dtr = False
        self._serial.rts = False

        time.sleep(2.0)
        self._serial.reset_input_buffer()

        self.pumps = ["A", "B", "C", "D"]
        print(f"--- PUMP DRIVER READY ON {port} ---", flush=True)

    # -------------------------
    # High-level setters
    # -------------------------
    def set_flow(self, pump: str, val: float) -> str:
        return self._transaction(self._build_set_cmd(pump, FLOW=val))

    def set_diameter(self, pump: str, val: float) -> str:
        return self._transaction(self._build_set_cmd(pump, DIAMETER=val))

    def set_direction(self, pump: str, val: str) -> str:
        return self._transaction(self._build_set_cmd(pump, DIRECTION=val))

    def set_state(self, pump: str, val: str) -> str:
        return self._transaction(self._build_set_cmd(pump, STATE=val))

    def set_unit(self, pump: str, val: str) -> str:
        return self._transaction(self._build_set_cmd(pump, UNIT=val))

    def set_gearbox(self, pump: str, val: str) -> str:
        return self._transaction(self._build_set_cmd(pump, GEARBOX=val))

    def set_microstep(self, pump: str, val: str) -> str:
        return self._transaction(self._build_set_cmd(pump, MICROSTEP=val))

    def set_threadrod(self, pump: str, val: str) -> str:
        return self._transaction(self._build_set_cmd(pump, ROD=val))

    def set_enable(self, pump: str, on: bool) -> str:
        return self._transaction(self._build_set_cmd(pump, ENABLE=("ON" if on else "OFF")))

    # -------------------------
    # GET helpers
    # -------------------------
    def get_pump_status(self, pump: str) -> str:
        return self._transaction(f"GET PUMP={pump} STATUS")

    def parse_status(self, response: str) -> dict[str, str]:
        """Parse key=value tokens from a status response."""
        data: dict[str, str] = {}
        parts = response.split()
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                data[key] = value
        return data

    def _parse_status_response(
        self, response: str, param_name: str, default: T, parser: Callable[[str], T]
    ) -> T:
        parts = response.split()
        for part in parts:
            if part.startswith(f"{param_name}="):
                value = part.split("=", 1)[1]
                try:
                    return parser(value)
                except (ValueError, IndexError):
                    pass
        return default

    def get_flow(self, pump: str) -> float:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "FLOW", 1000.0, float)

    def get_diameter(self, pump: str) -> float:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "DIAMETER", 8.17, float)

    def get_direction(self, pump: str) -> int:
        response = self.get_pump_status(pump)
        direction = self._parse_status_response(response, "DIRECTION", "INFUSE", str)
        return 1 if direction.upper() == "INFUSE" else -1

    def get_state(self, pump: str) -> bool:
        response = self.get_pump_status(pump)
        state = self._parse_status_response(response, "STATE", "STOP", str)
        return state.upper() == "RUN"

    def get_unit(self, pump: str) -> str:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "UNIT", "UL/HR", str)

    def get_gearbox(self, pump: str) -> str:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "GEARBOX", "1:1", str)

    def get_microstep(self, pump: str) -> str:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "MICROSTEP", "1/16", str)

    def get_threadrod(self, pump: str) -> str:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "ROD", "1-START", str)

    def get_enable(self, pump: str) -> bool:
        response = self.get_pump_status(pump)
        return self._parse_status_response(response, "ENABLE", "OFF", str) == "ON"

    # -------------------------
    # Internals
    # -------------------------
    def _build_set_cmd(self, pump: str, **kw) -> str:
        parts = [f"SET PUMP={pump}"]
        for k, v in kw.items():
            parts.append(f"{k}={v}")
        return " ".join(parts)

    def _transaction(self, cmd: str) -> str:
        with self._lock:
            full_cmd = cmd + "\n"
            print(f"--- SERIAL SEND: {repr(full_cmd)} ---", flush=True)

            self._serial.write(full_cmd.encode())

            response_bytes = cast(bytes, self._serial.readline())
            response = response_bytes.decode(errors="ignore").strip()
            print(f"--- SERIAL RECV: {repr(response)} ---", flush=True)
            return response

    def close(self) -> None:
        self._serial.close()
