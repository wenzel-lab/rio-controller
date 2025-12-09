"""
Simulated flow controller.

Mocks PIC-based flow/pressure control hardware for testing without physical hardware.
"""

import time
from typing import List, Tuple, Optional
import random


class SimulatedFlow:
    """
    Simulated flow controller (replaces PiFlow).
    
    Maintains internal state for 4-channel pressure/flow control.
    """
    
    DEVICE_ID = 'MICROFLOW'
    STX = 2
    PRESSURE_SHIFT = 3
    PRESSURE_SCALE = (1 << PRESSURE_SHIFT)
    
    # Packet types (matching real firmware)
    PACKET_TYPE_GET_ID = 1
    PACKET_TYPE_SET_PRESSURE_TARGET = 2
    PACKET_TYPE_GET_PRESSURE_TARGET = 3
    PACKET_TYPE_GET_PRESSURE_ACTUAL = 4
    PACKET_TYPE_SET_FLOW_TARGET = 5
    PACKET_TYPE_GET_FLOW_TARGET = 6
    PACKET_TYPE_GET_FLOW_ACTUAL = 7
    PACKET_TYPE_SET_CONTROL_MODE = 8
    PACKET_TYPE_GET_CONTROL_MODE = 9
    PACKET_TYPE_SET_FPID_CONSTS = 10
    PACKET_TYPE_GET_FPID_CONSTS = 11
    
    NUM_CONTROLLERS = 4
    
    # Control modes
    MODE_PRESSURE_OPEN_LOOP = 0
    MODE_PRESSURE_CLOSED_LOOP = 1
    MODE_FLOW_CLOSED_LOOP = 2
    
    def __init__(self, device_port: int, reply_pause_s: float = 0.1, num_channels: int = 4):
        """
        Initialize simulated flow controller.
        
        Args:
            device_port: GPIO port number (simulated)
            reply_pause_s: Reply pause time (simulated)
            num_channels: Number of flow channels
        """
        self.device_port = device_port
        self.reply_pause_s = reply_pause_s
        self.num_channels = num_channels
        
        # Internal state for each channel
        self.pressure_targets = [0.0] * num_channels
        self.pressure_actuals = [0.0] * num_channels
        self.flow_targets = [0.0] * num_channels
        self.flow_actuals = [0.0] * num_channels
        self.control_modes = [self.MODE_PRESSURE_OPEN_LOOP] * num_channels
        
        # PID constants (P, I, D) for each channel
        self.pid_consts = [[1000, 100, 0]] * num_channels  # Default PI constants (D=0)
        
        print(f"[SimulatedFlow] Initialized (port={device_port}, channels={num_channels})")
    
    def packet_query(self, type_: int, data: List[int]) -> Tuple[bool, List[int]]:
        """
        Query device (write + read response).
        
        Args:
            type_: Packet type
            data: Packet data
        
        Returns:
            (valid, response_data) tuple
        """
        # Simulate reply delay
        time.sleep(self.reply_pause_s)
        
        response = []
        valid = True
        
        if type_ == self.PACKET_TYPE_GET_ID:
            # Return device ID as ASCII bytes
            response = list(self.DEVICE_ID.encode('ascii'))
        
        elif type_ == self.PACKET_TYPE_SET_PRESSURE_TARGET:
            if len(data) >= 2:
                channel = data[0]
                pressure_raw = int.from_bytes(data[1:3], 'little', signed=False)
                pressure_mbar = pressure_raw / self.PRESSURE_SCALE
                if 0 <= channel < self.num_channels:
                    self.pressure_targets[channel] = pressure_mbar
                    # Simulate actual pressure approaching target
                    self.pressure_actuals[channel] = pressure_mbar * 0.95 + random.uniform(-10, 10)
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_PRESSURE_TARGET:
            if len(data) >= 1:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    pressure_raw = int(self.pressure_targets[channel] * self.PRESSURE_SCALE)
                    response = [0] + list(pressure_raw.to_bytes(2, 'little', signed=False))
        
        elif type_ == self.PACKET_TYPE_GET_PRESSURE_ACTUAL:
            if len(data) >= 1:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    # Simulate some variation
                    self.pressure_actuals[channel] += random.uniform(-5, 5)
                    self.pressure_actuals[channel] = max(0, min(self.pressure_actuals[channel], 6000))
                    pressure_raw = int(self.pressure_actuals[channel] * self.PRESSURE_SCALE)
                    response = [0] + list(pressure_raw.to_bytes(2, 'little', signed=False))
        
        elif type_ == self.PACKET_TYPE_SET_FLOW_TARGET:
            if len(data) >= 3:
                channel = data[0]
                flow_raw = int.from_bytes(data[1:3], 'little', signed=False)
                flow_ul_hr = flow_raw / 10.0  # Assuming 0.1 ul/hr resolution
                if 0 <= channel < self.num_channels:
                    self.flow_targets[channel] = flow_ul_hr
                    # Simulate actual flow approaching target
                    self.flow_actuals[channel] = flow_ul_hr * 0.9 + random.uniform(-5, 5)
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_FLOW_TARGET:
            if len(data) >= 1:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    flow_raw = int(self.flow_targets[channel] * 10.0)
                    response = [0] + list(flow_raw.to_bytes(2, 'little', signed=False))
        
        elif type_ == self.PACKET_TYPE_GET_FLOW_ACTUAL:
            if len(data) >= 1:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    # Simulate some variation
                    self.flow_actuals[channel] += random.uniform(-2, 2)
                    self.flow_actuals[channel] = max(0, min(self.flow_actuals[channel], 1000))
                    flow_raw = int(self.flow_actuals[channel] * 10.0)
                    response = [0] + list(flow_raw.to_bytes(2, 'little', signed=False))
        
        elif type_ == self.PACKET_TYPE_SET_CONTROL_MODE:
            if len(data) >= 2:
                channel = data[0]
                mode = data[1]
                if 0 <= channel < self.num_channels and 0 <= mode <= 2:
                    self.control_modes[channel] = mode
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_CONTROL_MODE:
            if len(data) >= 1:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    response = [0, self.control_modes[channel]]
        
        elif type_ == self.PACKET_TYPE_SET_FPID_CONSTS:
            if len(data) >= 10:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    # P, I, D as 3-byte values (little-endian)
                    p = int.from_bytes(data[1:4], 'little', signed=False)
                    i = int.from_bytes(data[4:7], 'little', signed=False)
                    d = int.from_bytes(data[7:10], 'little', signed=False)
                    self.pid_consts[channel] = [p, i, d]
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_FPID_CONSTS:
            if len(data) >= 1:
                channel = data[0]
                if 0 <= channel < self.num_channels:
                    p, i, d = self.pid_consts[channel]
                    response = [0]
                    response.extend(list(p.to_bytes(3, 'little', signed=False)))
                    response.extend(list(i.to_bytes(3, 'little', signed=False)))
                    response.extend(list(d.to_bytes(3, 'little', signed=False)))
        else:
            valid = False
        
        return valid, response
    
    # Convenience methods (matching PiFlow interface)
    def get_id(self) -> Tuple[bool, str]:
        """Get device ID."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_ID, [])
        if valid:
            device_id = bytes(data).decode('ascii', errors='ignore')
            return True, device_id
        return False, ''
    
    def set_pressure_target(self, channel: int, pressure_mbar: float) -> bool:
        """Set pressure target for channel."""
        pressure_raw = int(pressure_mbar * self.PRESSURE_SCALE)
        data = [channel] + list(pressure_raw.to_bytes(2, 'little', signed=False))
        valid, response = self.packet_query(self.PACKET_TYPE_SET_PRESSURE_TARGET, data)
        return valid and (response[0] == 0)
    
    def get_pressure_target(self, channel: int) -> Tuple[bool, float]:
        """Get pressure target for channel."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_PRESSURE_TARGET, [channel])
        if valid and len(data) >= 3:
            pressure_raw = int.from_bytes(data[1:3], 'little', signed=False)
            return True, pressure_raw / self.PRESSURE_SCALE
        return False, 0.0
    
    def get_pressure_actual(self, channel: int) -> Tuple[bool, float]:
        """Get actual pressure for channel."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_PRESSURE_ACTUAL, [channel])
        if valid and len(data) >= 3:
            pressure_raw = int.from_bytes(data[1:3], 'little', signed=False)
            return True, pressure_raw / self.PRESSURE_SCALE
        return False, 0.0
    
    def set_flow_target(self, channel: int, flow_ul_hr: float) -> bool:
        """Set flow target for channel."""
        flow_raw = int(flow_ul_hr * 10.0)
        data = [channel] + list(flow_raw.to_bytes(2, 'little', signed=False))
        valid, response = self.packet_query(self.PACKET_TYPE_SET_FLOW_TARGET, data)
        return valid and (response[0] == 0)
    
    def get_flow_target(self, channel: int) -> Tuple[bool, float]:
        """Get flow target for channel."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_FLOW_TARGET, [channel])
        if valid and len(data) >= 3:
            flow_raw = int.from_bytes(data[1:3], 'little', signed=False)
            return True, flow_raw / 10.0
        return False, 0.0
    
    def get_flow_actual(self, channel: int) -> Tuple[bool, float]:
        """Get actual flow for channel."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_FLOW_ACTUAL, [channel])
        if valid and len(data) >= 3:
            flow_raw = int.from_bytes(data[1:3], 'little', signed=False)
            return True, flow_raw / 10.0
        return False, 0.0
    
    def set_control_mode(self, channel: int, mode: int) -> bool:
        """Set control mode for channel."""
        valid, response = self.packet_query(self.PACKET_TYPE_SET_CONTROL_MODE, [channel, mode])
        return valid and (response[0] == 0)
    
    def get_control_mode(self, channel: int) -> Tuple[bool, int]:
        """Get control mode for channel."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_CONTROL_MODE, [channel])
        if valid and len(data) >= 2:
            return True, data[1]
        return False, 0
    
    def set_fpid_consts(self, channel: int, p: int, i: int, d: int) -> bool:
        """Set PID constants for channel."""
        data = [channel]
        data.extend(list(p.to_bytes(3, 'little', signed=False)))
        data.extend(list(i.to_bytes(3, 'little', signed=False)))
        data.extend(list(d.to_bytes(3, 'little', signed=False)))
        valid, response = self.packet_query(self.PACKET_TYPE_SET_FPID_CONSTS, data)
        return valid and (response[0] == 0)
    
    def get_fpid_consts(self, channel: int) -> Tuple[bool, int, int, int]:
        """Get PID constants for channel."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_FPID_CONSTS, [channel])
        if valid and len(data) >= 10:
            p = int.from_bytes(data[1:4], 'little', signed=False)
            i = int.from_bytes(data[4:7], 'little', signed=False)
            d = int.from_bytes(data[7:10], 'little', signed=False)
            return True, p, i, d
        return False, 0, 0, 0

