"""
Simulated heater controller.

Provides responses for heater SPI commands to support simulation mode.
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class SimulatedHeater:
    DEVICE_ID = "SAMPLE_HOLDER"
    PACKET_TYPE_GET_ID = 1
    PACKET_TYPE_TEMP_SET_TARGET = 2
    PACKET_TYPE_TEMP_GET_TARGET = 3
    PACKET_TYPE_TEMP_GET_ACTUAL = 4
    PACKET_TYPE_PID_SET_COEFFS = 5
    PACKET_TYPE_PID_GET_COEFFS = 6
    PACKET_TYPE_PID_SET_RUNNING = 7
    PACKET_TYPE_PID_GET_STATUS = 8
    PACKET_TYPE_AUTOTUNE_SET_RUNNING = 9
    PACKET_TYPE_AUTOTUNE_GET_RUNNING = 10
    PACKET_TYPE_AUTOTUNE_GET_STATUS = 11
    PACKET_TYPE_STIR_SET_RUNNING = 12
    PACKET_TYPE_STIR_GET_STATUS = 13
    PACKET_TYPE_STIR_SPEED_GET_ACTUAL = 14
    PACKET_TYPE_HEAT_POWER_LIMIT_SET = 15
    PACKET_TYPE_HEAT_POWER_LIMIT_GET = 16

    def __init__(self, device_port: int, reply_pause_s: float = 0.05):
        self.device_port = device_port
        self.reply_pause_s = reply_pause_s
        # Default simulated state
        self.temp_c = 25.0  # Celsius
        self.pid_p = 0
        self.pid_i = 0
        self.pid_d = 0
        self.pid_running = False
        self.autotune_running = False
        self.autotune_status = 0
        self.autotune_fail = 0
        self.stir_running = False
        self.stir_speed_rps = 0
        self.heat_power_limit_pc = 100

    def _status_ok(self) -> List[int]:
        return [0]

    def packet_query(  # noqa: C901
        self, packet_type: int, data: List[int]
    ) -> Tuple[bool, List[int]]:
        """
        Handle heater packet queries.

        Returns:
            (valid, response_data)
            response_data is the payload (without STX/size/type/checksum)
        """
        try:
            if packet_type == self.PACKET_TYPE_GET_ID:
                payload = [0]
                payload.extend(list(self.DEVICE_ID.encode("ascii")))
                payload.append(0)
                return True, payload

            if packet_type == self.PACKET_TYPE_TEMP_SET_TARGET:
                # Accept target, store it
                if len(data) >= 2:
                    val = int.from_bytes(data[0:2], "little", signed=True)
                    self.temp_c = val / 100.0
                return True, self._status_ok()

            if packet_type == self.PACKET_TYPE_TEMP_GET_TARGET:
                # Return status + temp target (2 bytes, big endian, signed)
                temp_scaled = int(self.temp_c * 100)
                temp_bytes = temp_scaled.to_bytes(2, "big", signed=True)
                return True, [0, temp_bytes[0], temp_bytes[1]]

            if packet_type == self.PACKET_TYPE_TEMP_GET_ACTUAL:
                temp_scaled = int(self.temp_c * 100)
                temp_bytes = temp_scaled.to_bytes(2, "big", signed=True)
                return True, [0, temp_bytes[0], temp_bytes[1]]

            if packet_type == self.PACKET_TYPE_PID_SET_COEFFS:
                if len(data) >= 6:
                    self.pid_p = int.from_bytes(data[0:2], "little", signed=False)
                    self.pid_i = int.from_bytes(data[2:4], "little", signed=False)
                    self.pid_d = int.from_bytes(data[4:6], "little", signed=False)
                return True, self._status_ok()

            if packet_type == self.PACKET_TYPE_PID_GET_COEFFS:
                p_bytes = self.pid_p.to_bytes(2, "big", signed=False)
                i_bytes = self.pid_i.to_bytes(2, "big", signed=False)
                d_bytes = self.pid_d.to_bytes(2, "big", signed=False)
                return True, [
                    0,
                    p_bytes[0],
                    p_bytes[1],
                    i_bytes[0],
                    i_bytes[1],
                    d_bytes[0],
                    d_bytes[1],
                ]

            if packet_type == self.PACKET_TYPE_PID_SET_RUNNING:
                if len(data) >= 1:
                    self.pid_running = bool(data[0])
                return True, self._status_ok()

            if packet_type == self.PACKET_TYPE_PID_GET_STATUS:
                # status byte + pid_status + pid_error
                pid_status = 1 if self.pid_running else 0
                pid_error = 0
                return True, [0, pid_status, pid_error]

            if packet_type == self.PACKET_TYPE_AUTOTUNE_SET_RUNNING:
                if len(data) >= 3:
                    self.autotune_running = bool(data[0])
                    # ignore target temp for now
                return True, self._status_ok()

            if packet_type == self.PACKET_TYPE_AUTOTUNE_GET_RUNNING:
                return True, [0, 1 if self.autotune_running else 0]

            if packet_type == self.PACKET_TYPE_AUTOTUNE_GET_STATUS:
                return True, [0, self.autotune_status, self.autotune_fail]

            if packet_type == self.PACKET_TYPE_STIR_SET_RUNNING:
                if len(data) >= 3:
                    self.stir_running = bool(data[0])
                    self.stir_speed_rps = int.from_bytes(data[1:3], "little", signed=False)
                return True, self._status_ok()

            if packet_type == self.PACKET_TYPE_STIR_GET_STATUS:
                stir_status = 1 if self.stir_running else 0
                return True, [0, stir_status]

            if packet_type == self.PACKET_TYPE_STIR_SPEED_GET_ACTUAL:
                speed_bytes = self.stir_speed_rps.to_bytes(2, "big", signed=False)
                return True, [0, speed_bytes[0], speed_bytes[1]]

            if packet_type == self.PACKET_TYPE_HEAT_POWER_LIMIT_SET:
                if len(data) >= 1:
                    self.heat_power_limit_pc = data[0]
                return True, self._status_ok()

            if packet_type == self.PACKET_TYPE_HEAT_POWER_LIMIT_GET:
                return True, [0, self.heat_power_limit_pc]

            # Unknown packet: return failure
            logger.warning(f"Unknown heater packet type: {packet_type}")
            return False, []

        except Exception as e:
            logger.error(f"Error in heater simulation: {e}")
            return False, []
