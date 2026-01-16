"""Simulated syringe pump controller (no hardware required)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class _PumpState:
    flow: float = 1000.0
    diameter: float = 8.17
    direction: int = 1  # 1 infuse, -1 withdraw
    state: bool = False  # running
    unit: str = "UL/HR"
    gearbox: str = "1:1"
    microstep: str = "1/16"
    threadrod: str = "1-START"
    enabled: bool = True


class SimulatedPump:
    """Simulation backend that mimics the serial pump protocol."""

    def __init__(self) -> None:
        self.pumps: Dict[str, _PumpState] = {
            "A": _PumpState(),
            "B": _PumpState(),
            "C": _PumpState(),
            "D": _PumpState(),
        }

    def _get(self, pump: str) -> _PumpState:
        if pump not in self.pumps:
            raise ValueError(f"Invalid pump '{pump}' (expected A-D)")
        return self.pumps[pump]

    # Setters
    def set_flow(self, pump: str, val: float) -> str:
        self._get(pump).flow = float(val)
        return "OK"

    def set_diameter(self, pump: str, val: float) -> str:
        self._get(pump).diameter = float(val)
        return "OK"

    def set_direction(self, pump: str, val: str) -> str:
        state = self._get(pump)
        if str(val).upper() in ("INFUSE", "1"):
            state.direction = 1
        else:
            state.direction = -1
        return "OK"

    def set_state(self, pump: str, val: str) -> str:
        state = self._get(pump)
        state.state = str(val).upper() in ("RUN", "TRUE", "1")
        return "OK"

    def set_unit(self, pump: str, val: str) -> str:
        self._get(pump).unit = str(val)
        return "OK"

    def set_gearbox(self, pump: str, val: str) -> str:
        self._get(pump).gearbox = str(val)
        return "OK"

    def set_microstep(self, pump: str, val: str) -> str:
        self._get(pump).microstep = str(val)
        return "OK"

    def set_threadrod(self, pump: str, val: str) -> str:
        self._get(pump).threadrod = str(val)
        return "OK"

    def set_enable(self, pump: str, on: bool) -> str:
        self._get(pump).enabled = bool(on)
        return "OK"

    # Status and getters
    def get_pump_status(self, pump: str) -> str:
        state = self._get(pump)
        direction = "INFUSE" if state.direction >= 0 else "WITHDRAW"
        run_state = "RUN" if state.state else "STOP"
        enabled = "ON" if state.enabled else "OFF"
        return (
            f"PUMP={pump} FLOW={state.flow} DIAMETER={state.diameter} "
            f"DIRECTION={direction} STATE={run_state} UNIT={state.unit} "
            f"GEARBOX={state.gearbox} MICROSTEP={state.microstep} "
            f"ROD={state.threadrod} ENABLE={enabled}"
        )

    def parse_status(self, response: str) -> dict[str, str]:
        data: dict[str, str] = {}
        parts = response.split()
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                data[key] = value
        return data

    def get_flow(self, pump: str) -> float:
        return self._get(pump).flow

    def get_diameter(self, pump: str) -> float:
        return self._get(pump).diameter

    def get_direction(self, pump: str) -> int:
        return self._get(pump).direction

    def get_state(self, pump: str) -> bool:
        return self._get(pump).state

    def get_unit(self, pump: str) -> str:
        return self._get(pump).unit

    def get_gearbox(self, pump: str) -> str:
        return self._get(pump).gearbox

    def get_microstep(self, pump: str) -> str:
        return self._get(pump).microstep

    def get_threadrod(self, pump: str) -> str:
        return self._get(pump).threadrod

    def get_enable(self, pump: str) -> bool:
        return self._get(pump).enabled
