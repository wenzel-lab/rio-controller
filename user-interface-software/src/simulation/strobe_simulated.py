"""
Simulated strobe controller.

Mocks PIC-based strobe hardware for testing without physical hardware.
"""

import time
from typing import Optional, Tuple


class SimulatedStrobe:
    """
    Simulated strobe controller (replaces PiStrobe).
    
    Maintains internal state and simulates PIC communication protocol.
    """
    
    STX = 2
    
    # Packet types (matching real firmware)
    PACKET_TYPE_SET_ENABLE = 1
    PACKET_TYPE_GET_ENABLE = 2
    PACKET_TYPE_SET_TIMING = 3
    PACKET_TYPE_GET_TIMING = 4
    PACKET_TYPE_SET_HOLD = 5
    PACKET_TYPE_GET_HOLD = 6
    PACKET_TYPE_GET_CAM_READ_TIME = 7
    PACKET_TYPE_SET_TRIGGER_MODE = 8
    
    def __init__(self, device_port: int, reply_pause_s: float = 0.1):
        """
        Initialize simulated strobe.
        
        Args:
            device_port: GPIO port number (simulated)
            reply_pause_s: Reply pause time (simulated)
        """
        self.device_port = device_port
        self.reply_pause_s = reply_pause_s
        
        # Internal state
        self.enabled = False
        self.hold = False
        self.wait_ns = 0
        self.period_ns = 100000  # Default 100us
        self.trigger_mode = False  # Hardware trigger mode
        self.cam_read_time_us = 10000  # Simulated camera read time
        
        print(f"[SimulatedStrobe] Initialized (port={device_port})")
    
    def packet_read(self) -> Tuple[bool, Optional[int], list]:
        """
        Read packet from SPI (simulated).
        
        Returns:
            (valid, type, data) tuple
        """
        # In simulation, we don't actually read from SPI
        # This would be called by the SPI handler
        return False, None, []
    
    def packet_write(self, type_: int, data: list):
        """Write packet to SPI (simulated)."""
        # Process command based on packet type
        if type_ == self.PACKET_TYPE_SET_ENABLE:
            if len(data) >= 1:
                self.enabled = bool(data[0])
                print(f"[SimulatedStrobe] Enable set to {self.enabled}")
        elif type_ == self.PACKET_TYPE_SET_TIMING:
            if len(data) >= 2:
                self.wait_ns = int.from_bytes(data[0:4], 'little', signed=False)
                self.period_ns = int.from_bytes(data[4:8], 'little', signed=False)
                print(f"[SimulatedStrobe] Timing: wait={self.wait_ns}ns, period={self.period_ns}ns")
        elif type_ == self.PACKET_TYPE_SET_HOLD:
            if len(data) >= 1:
                self.hold = bool(data[0])
                print(f"[SimulatedStrobe] Hold set to {self.hold}")
        elif type_ == self.PACKET_TYPE_SET_TRIGGER_MODE:
            if len(data) >= 1:
                self.trigger_mode = bool(data[0])
                print(f"[SimulatedStrobe] Trigger mode set to {self.trigger_mode}")
    
    def packet_query(self, type_: int, data: list) -> Tuple[bool, list]:
        """
        Query device (write + read response).
        
        Args:
            type_: Packet type
            data: Packet data
        
        Returns:
            (valid, response_data) tuple
        """
        # Write command
        self.packet_write(type_, data)
        
        # Simulate reply delay
        time.sleep(self.reply_pause_s)
        
        # Generate response based on packet type
        response = []
        valid = True
        
        if type_ == self.PACKET_TYPE_GET_ENABLE:
            response = [1 if self.enabled else 0]
        elif type_ == self.PACKET_TYPE_GET_TIMING:
            # Return wait_ns and period_ns as 4-byte little-endian
            response = list(self.wait_ns.to_bytes(4, 'little', signed=False))
            response.extend(list(self.period_ns.to_bytes(4, 'little', signed=False)))
        elif type_ == self.PACKET_TYPE_GET_HOLD:
            response = [1 if self.hold else 0]
        elif type_ == self.PACKET_TYPE_GET_CAM_READ_TIME:
            # Return as 4-byte little-endian (microseconds)
            response = list(self.cam_read_time_us.to_bytes(4, 'little', signed=False))
        elif type_ == self.PACKET_TYPE_SET_ENABLE:
            response = [0]  # Success
        elif type_ == self.PACKET_TYPE_SET_TIMING:
            response = [0]  # Success
        elif type_ == self.PACKET_TYPE_SET_HOLD:
            response = [0]  # Success
        elif type_ == self.PACKET_TYPE_SET_TRIGGER_MODE:
            response = [0]  # Success
        else:
            valid = False
        
        return valid, response
    
    # Convenience methods (matching PiStrobe interface)
    def set_enable(self, enable: bool) -> bool:
        """Enable/disable strobe."""
        valid, data = self.packet_query(self.PACKET_TYPE_SET_ENABLE, [1 if enable else 0])
        return valid and (data[0] == 0)
    
    def get_enable(self) -> Tuple[bool, bool]:
        """Get enable state."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_ENABLE, [])
        if valid and len(data) >= 1:
            return True, bool(data[0])
        return False, False
    
    def set_timing(self, wait_ns: int, period_ns: int) -> Tuple[bool, int, int]:
        """Set strobe timing."""
        data = list(wait_ns.to_bytes(4, 'little', signed=False))
        data.extend(list(period_ns.to_bytes(4, 'little', signed=False)))
        valid, response = self.packet_query(self.PACKET_TYPE_SET_TIMING, data)
        if valid:
            return True, self.wait_ns, self.period_ns
        return False, 0, 0
    
    def get_timing(self) -> Tuple[bool, int, int]:
        """Get strobe timing."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_TIMING, [])
        if valid and len(data) >= 8:
            wait_ns = int.from_bytes(data[0:4], 'little', signed=False)
            period_ns = int.from_bytes(data[4:8], 'little', signed=False)
            return True, wait_ns, period_ns
        return False, 0, 0
    
    def set_hold(self, hold: bool) -> bool:
        """Set hold state."""
        valid, data = self.packet_query(self.PACKET_TYPE_SET_HOLD, [1 if hold else 0])
        return valid and (data[0] == 0)
    
    def get_hold(self) -> Tuple[bool, bool]:
        """Get hold state."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_HOLD, [])
        if valid and len(data) >= 1:
            return True, bool(data[0])
        return False, False
    
    def get_cam_read_time(self) -> Tuple[bool, int]:
        """Get camera read time (simulated)."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_CAM_READ_TIME, [])
        if valid and len(data) >= 4:
            cam_read_time_us = int.from_bytes(data[0:4], 'little', signed=False)
            return True, cam_read_time_us
        return False, 0
    
    def set_trigger_mode(self, hardware_trigger: bool) -> bool:
        """Set trigger mode (hardware vs software)."""
        valid, data = self.packet_query(self.PACKET_TYPE_SET_TRIGGER_MODE, [1 if hardware_trigger else 0])
        return valid and (data[0] == 0)

