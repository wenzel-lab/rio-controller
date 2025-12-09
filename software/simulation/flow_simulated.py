"""
Simulated flow controller.

Mocks PIC-based flow/pressure control hardware for testing without physical hardware.
This module provides a drop-in replacement for the real PiFlow class,
allowing the application to run and be tested on any system.

Classes:
    SimulatedFlow: Flow controller implementation that simulates PIC behavior
"""

import time
import logging
from typing import List, Tuple, Optional
import random

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_REPLY_PAUSE_S = 0.1
DEFAULT_NUM_CHANNELS = 4
DEFAULT_PRESSURE_RANGE = (0, 6000)  # mbar
DEFAULT_FLOW_RANGE = (0, 1000)  # ul/hr


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
    
    # Control modes (matching real firmware)
    MODE_OFF = 0
    MODE_PRESSURE_OPEN_LOOP = 1
    MODE_PRESSURE_CLOSED_LOOP = 2
    MODE_FLOW_CLOSED_LOOP = 3
    
    def __init__(self, device_port: int, reply_pause_s: float = DEFAULT_REPLY_PAUSE_S,
                 num_channels: int = DEFAULT_NUM_CHANNELS):
        """
        Initialize simulated flow controller.
        
        Args:
            device_port: GPIO port number (simulated)
            reply_pause_s: Reply pause time in seconds (simulated, default: 0.1)
            num_channels: Number of flow channels (default: 4)
        
        Raises:
            ValueError: If device_port, reply_pause_s, or num_channels are invalid
        """
        if device_port < 0:
            raise ValueError(f"Invalid device port: {device_port}")
        if reply_pause_s < 0:
            raise ValueError(f"Invalid reply pause time: {reply_pause_s}")
        if num_channels <= 0:
            raise ValueError(f"Invalid number of channels: {num_channels}")
        
        self.device_port = device_port
        self.reply_pause_s = reply_pause_s
        self.num_channels = num_channels
        
        logger.debug(f"SimulatedFlow initialized (port={device_port}, channels={num_channels})")
        
        # Internal state for each channel
        self.pressure_targets = [0.0] * num_channels
        self.pressure_actuals = [0.0] * num_channels
        self.flow_targets = [0.0] * num_channels
        self.flow_actuals = [0.0] * num_channels
        self.control_modes = [self.MODE_OFF] * num_channels  # Default to Off
        
        # PID constants (P, I, D) for each channel - stored as U16 values
        self.pid_consts = [[0, 0, 0]] * num_channels  # Default: all zeros
    
    def packet_query(self, type_: int, data: List[int]) -> Tuple[bool, List[int]]:
        """
        Query device (write + read response).
        
        Simulates the SPI query protocol: process command, wait for reply,
        then return response data matching the real firmware format.
        
        Args:
            type_: Packet type (PACKET_TYPE_* constant)
            data: Packet data bytes
        
        Returns:
            Tuple of (valid, response_data) where:
            - valid: True if query was successful
            - response_data: Response bytes from simulated device
        """
        # Simulate reply delay (PIC processing time)
        time.sleep(self.reply_pause_s)
        
        response = []
        valid = True
        
        if type_ == self.PACKET_TYPE_GET_ID:
            # Return device ID as ASCII bytes
            response = list(self.DEVICE_ID.encode('ascii'))
        
        elif type_ == self.PACKET_TYPE_SET_PRESSURE_TARGET:
            # Real firmware format: mask (U8) + pressure (U16) for each channel
            # Multiple channels can be set in one packet
            i = 0
            while i < len(data):
                if i + 2 < len(data):
                    mask = data[i]
                    pressure_raw = int.from_bytes(data[i+1:i+3], 'little', signed=False)
                    pressure_mbar = pressure_raw / self.PRESSURE_SCALE
                    # Process each channel in mask
                    for channel in range(self.num_channels):
                        if mask & (1 << channel):
                            self.pressure_targets[channel] = pressure_mbar
                            # Simulate actual pressure approaching target
                            self.pressure_actuals[channel] = pressure_mbar * 0.95 + random.uniform(-10, 10)
                    i += 3
                else:
                    break
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_PRESSURE_TARGET:
            # Real firmware returns [0] + pressure (U16) for each channel
            response = [0]
            for channel in range(self.num_channels):
                pressure_raw = int(self.pressure_targets[channel] * self.PRESSURE_SCALE)
                response.extend(list(pressure_raw.to_bytes(2, 'little', signed=False)))
        
        elif type_ == self.PACKET_TYPE_GET_PRESSURE_ACTUAL:
            # Real firmware returns [0] + pressure (S16) for each channel (signed for actual)
            response = [0]
            for channel in range(self.num_channels):
                # Simulate some variation
                self.pressure_actuals[channel] += random.uniform(-5, 5)
                self.pressure_actuals[channel] = max(0, min(self.pressure_actuals[channel], 6000))
                pressure_raw = int(self.pressure_actuals[channel] * self.PRESSURE_SCALE)
                response.extend(list(pressure_raw.to_bytes(2, 'little', signed=True)))
        
        elif type_ == self.PACKET_TYPE_SET_FLOW_TARGET:
            # Real firmware format: mask (U8) + flow (U16) for each channel
            # Flow is in ul/hr as U16 (no scaling)
            i = 0
            while i < len(data):
                if i + 2 < len(data):
                    mask = data[i]
                    flow_ul_hr = int.from_bytes(data[i+1:i+3], 'little', signed=False)
                    # Process each channel in mask
                    for channel in range(self.num_channels):
                        if mask & (1 << channel):
                            self.flow_targets[channel] = float(flow_ul_hr)
                            # Simulate actual flow approaching target
                            self.flow_actuals[channel] = flow_ul_hr * 0.9 + random.uniform(-5, 5)
                    i += 3
                else:
                    break
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_FLOW_TARGET:
            # Real firmware returns [0] + flow (U16) for each channel
            response = [0]
            for channel in range(self.num_channels):
                flow_ul_hr = int(self.flow_targets[channel])
                response.extend(list(flow_ul_hr.to_bytes(2, 'little', signed=False)))
        
        elif type_ == self.PACKET_TYPE_GET_FLOW_ACTUAL:
            # Real firmware returns [0] + flow (S16) for each channel (signed for actual)
            response = [0]
            for channel in range(self.num_channels):
                # Simulate some variation
                self.flow_actuals[channel] += random.uniform(-2, 2)
                self.flow_actuals[channel] = max(0, min(self.flow_actuals[channel], 1000))
                flow_ul_hr = int(self.flow_actuals[channel])
                response.extend(list(flow_ul_hr.to_bytes(2, 'little', signed=True)))
        
        elif type_ == self.PACKET_TYPE_SET_CONTROL_MODE:
            # Real firmware format: mask (U8) + mode (U8) for each channel
            i = 0
            while i < len(data):
                if i + 1 < len(data):
                    mask = data[i]
                    mode = data[i + 1]
                    # Process each channel in mask
                    for channel in range(self.num_channels):
                        if mask & (1 << channel):
                            if 0 <= mode <= 3:  # 0=Off, 1=Pressure Open Loop, 2=Pressure Closed Loop, 3=Flow Closed Loop
                                self.control_modes[channel] = mode
                    i += 2
                else:
                    break
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_CONTROL_MODE:
            # Real firmware returns [0] + mode (U8) for each channel
            response = [0]
            for channel in range(self.num_channels):
                response.append(self.control_modes[channel])
        
        elif type_ == self.PACKET_TYPE_SET_FPID_CONSTS:
            # Real firmware format: mask (U8) + P (U16) + I (U16) + D (U16) for each channel
            i = 0
            while i < len(data):
                if i + 6 < len(data):
                    mask = data[i]
                    p = int.from_bytes(data[i+1:i+3], 'little', signed=False)
                    i_val = int.from_bytes(data[i+3:i+5], 'little', signed=False)
                    d = int.from_bytes(data[i+5:i+7], 'little', signed=False)
                    # Process each channel in mask
                    for channel in range(self.num_channels):
                        if mask & (1 << channel):
                            self.pid_consts[channel] = [p, i_val, d]
                    i += 7
                else:
                    break
            response = [0]  # Success
        
        elif type_ == self.PACKET_TYPE_GET_FPID_CONSTS:
            # Real firmware returns [0] + P (U16) + I (U16) + D (U16) for each channel
            response = [0]
            for channel in range(self.num_channels):
                p, i_val, d = self.pid_consts[channel]
                response.extend(list(p.to_bytes(2, 'little', signed=False)))
                response.extend(list(i_val.to_bytes(2, 'little', signed=False)))
                response.extend(list(d.to_bytes(2, 'little', signed=False)))
        else:
            valid = False
            logger.warning(f"Unknown packet type in query: {type_}")
        
        if not valid:
            logger.debug(f"Invalid packet query: type={type_}, data_len={len(data)}")
        
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

