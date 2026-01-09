"""
WebSocket aggregator and capture support.

This provides a single WS endpoint that can multiplex flow/pressure/heater topics.
Sampling is pull-based on the server at a configured interval; clients can request
topics/channels and an optional max_hz cap. Capture to CSV is optional and
disabled by default.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from config import CONTROL_MODE_FIRMWARE_TO_UI

# Types
FlowControllerType = Any  # controllers.flow_web.FlowWeb
HeatersType = List[Any]  # list[heater_web]


@dataclass
class CaptureConfig:
    enabled: bool = False
    topics: List[str] = field(default_factory=list)
    channels: Dict[str, List[int]] = field(default_factory=dict)
    path: Optional[Path] = None
    writer: Optional[csv.writer] = None
    file_handle: Any = None


class Aggregator:
    """
    Collects telemetry from controllers and serves it over a single WebSocket.
    Also supports optional CSV capture (off by default).
    """

    def __init__(
        self,
        flow: Optional[FlowControllerType],
        heaters: Optional[HeatersType],
        channel_config: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> None:
        self.flow = flow
        self.heaters = heaters
        self.channel_config = channel_config
        self.seq = {"flow": 0, "pressure": 0, "heater": 0}
        self.capture = CaptureConfig()

    async def handle_ws(self, websocket: WebSocket):
        await websocket.accept()
        try:
            init_msg = await websocket.receive_text()
            sub = json.loads(init_msg)
            topics: List[str] = sub.get("topics", ["flow", "pressure", "heater"])
            channels: Dict[str, List[int]] = sub.get("channels", {})
            max_hz: float = float(sub.get("max_hz", 10.0))
            interval = max(0.01, 1.0 / max_hz)

            while True:
                await self._emit(websocket, topics, channels)
                await asyncio.sleep(interval)
        except WebSocketDisconnect:
            return
        except Exception:
            await websocket.close()
            return

    async def _emit(self, websocket: WebSocket, topics: List[str], channels: Dict[str, List[int]]):
        now = datetime.utcnow().isoformat() + "Z"
        if "flow" in topics or "pressure" in topics:
            payload = await self._sample_flow(now, channels.get("flow", []))
            if payload:
                await websocket.send_json(payload)
                self._maybe_capture("flow", payload)
        if "heater" in topics:
            payload = await self._sample_heater(now, channels.get("heater", []))
            if payload:
                await websocket.send_json(payload)
                self._maybe_capture("heater", payload)

    async def _sample_flow(self, ts: str, channel_list: List[int]) -> Optional[Dict[str, Any]]:
        if self.flow is None:
            return None
        num = self.flow.flow.NUM_CONTROLLERS
        chans = channel_list if channel_list else list(range(num))
        # Update cached targets/modes
        self.flow.get_pressure_targets()
        self.flow.get_flow_targets()
        self.flow.get_control_modes()

        pressure_actuals: list[float] = []
        flow_actuals: list[float] = []
        pressure_targets: list[float] = self.flow.pressure_mbar_targets
        flow_targets: list[float] = self.flow.flow_ul_hr_targets
        control_modes_fw: list[int] = self.flow.control_modes
        control_modes_ui: list[int] = [CONTROL_MODE_FIRMWARE_TO_UI.get(m, 0) for m in control_modes_fw]

        for i in chans:
            ok_p, p_val = self.flow.flow.get_pressure_actual(i)
            ok_f, f_val = self.flow.flow.get_flow_actual(i)
            # apply calibration if present
            calib = self._get_calibration("flow", i)
            p_val_adj = (p_val if ok_p else 0.0) * calib
            f_val_adj = (f_val if ok_f else 0.0) * calib
            pressure_actuals.append(p_val_adj)
            flow_actuals.append(f_val_adj)

        names = [self._get_name("flow", i) for i in chans]

        self.seq["flow"] += 1
        return {
            "topic": "flow",
            "seq": self.seq["flow"],
            "t0": ts,
            "dt_ms": None,
            "channels": chans,
            "names": names,
            "units": {"pressure_mbar": "mbar", "flow_ul_hr": "uL/hr"},
            "samples": [
                {
                    "pressure_targets_mbar": pressure_targets,
                    "pressure_actuals_mbar": pressure_actuals,
                    "flow_targets_ul_hr": flow_targets,
                    "flow_actuals_ul_hr": flow_actuals,
                    "control_modes_ui": control_modes_ui,
                }
            ],
        }

    async def _sample_heater(self, ts: str, channel_list: List[int]) -> Optional[Dict[str, Any]]:
        if self.heaters is None:
            return None
        chans = channel_list if channel_list else list(range(len(self.heaters)))
        for h in self.heaters:
            h.update()
        items = []
        for i in chans:
            h = self.heaters[i]
            items.append(
                {
                    "temp_c_actual": h.temp_c_actual,
                    "temp_c_target": h.temp_c_target,
                    "pid_enabled": h.pid_enabled,
                    "stir_enabled": h.stir_enabled,
                    "autotuning": h.autotuning,
                    "status_text": h.status_text,
                }
            )
        names = [self._get_name("heater", i) for i in chans]
        self.seq["heater"] += 1
        return {
            "topic": "heater",
            "seq": self.seq["heater"],
            "t0": ts,
            "dt_ms": None,
            "channels": chans,
            "names": names,
            "units": {"temp_c": "C"},
            "samples": items,
        }

    def _get_name(self, topic: str, idx: int) -> str:
        try:
            return str(self.channel_config.get(topic, {}).get(str(idx), {}).get("name", "") or "")
        except Exception:
            return ""

    def _get_calibration(self, topic: str, idx: int) -> float:
        try:
            val = self.channel_config.get(topic, {}).get(str(idx), {}).get("calibration_factor")
            if val is None:
                return 1.0
            return float(val)
        except Exception:
            return 1.0

    # Capture support
    def start_capture(self, topics: List[str], channels: Dict[str, List[int]], path: str | None = None):
        if self.capture.enabled:
            self.stop_capture()
        if path is None:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = f"./capture_{ts}.csv"
        fh = open(path, "w", newline="")
        writer = csv.writer(fh)
        writer.writerow(["ts", "topic", "channels", "payload_json"])
        self.capture = CaptureConfig(
            enabled=True, topics=topics, channels=channels, path=Path(path), writer=writer, file_handle=fh
        )

    def stop_capture(self):
        if self.capture.file_handle:
            try:
                self.capture.file_handle.close()
            except Exception:
                pass
        self.capture = CaptureConfig()

    def capture_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.capture.enabled,
            "path": str(self.capture.path) if self.capture.path else None,
            "topics": self.capture.topics,
            "channels": self.capture.channels,
        }

    def _maybe_capture(self, topic: str, payload: Dict[str, Any]):
        if not self.capture.enabled:
            return
        if topic not in self.capture.topics:
            return
        try:
            self.capture.writer.writerow(
                [
                    datetime.utcnow().isoformat() + "Z",
                    topic,
                    json.dumps(self.capture.channels.get(topic, [])),
                    json.dumps(payload),
                ]
            )
        except Exception:
            return

