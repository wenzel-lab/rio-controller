"""
Simulated strobe controller.

Mocks PIC-based strobe hardware for testing without physical hardware.
This module provides a drop-in replacement for the real PiStrobe class,
allowing the application to run and be tested on any system.

Classes:
    SimulatedStrobe: Strobe controller implementation that simulates PIC behavior
"""

import time
import logging
from typing import Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_REPLY_PAUSE_S = 0.1
DEFAULT_PERIOD_NS = 100000  # 100 microseconds
DEFAULT_CAM_READ_TIME_US = 10000  # 10 milliseconds


class SimulatedStrobe:
    """
    Simulated strobe controller (replaces PiStrobe).
    
    Maintains internal state and simulates PIC communication protocol.
    """
    
    STX = 2
    
    # Packet types (matching real firmware - see pistrobe.py)
    # Note: Real firmware uses same packet type for set/get in some cases
    PACKET_TYPE_SET_ENABLE = 1  # Also used for GET_ID
    PACKET_TYPE_SET_TIMING = 2
    PACKET_TYPE_SET_HOLD = 3
    PACKET_TYPE_GET_CAM_READ_TIME = 4
    PACKET_TYPE_SET_TRIGGER_MODE = 5
    
    def __init__(self, device_port: int, reply_pause_s: float = DEFAULT_REPLY_PAUSE_S):
        """
        Initialize simulated strobe.
        
        Args:
            device_port: GPIO port number (simulated)
            reply_pause_s: Reply pause time in seconds (simulated, default: 0.1)
        
        Raises:
            ValueError: If device_port or reply_pause_s are invalid
        """
        if device_port < 0:
            raise ValueError(f"Invalid device port: {device_port}")
        if reply_pause_s < 0:
            raise ValueError(f"Invalid reply pause time: {reply_pause_s}")
        
        self.device_port = device_port
        self.reply_pause_s = reply_pause_s
        
        # Internal state
        self.enabled = False
        self.hold = False
        self.wait_ns = 0
        self.period_ns = DEFAULT_PERIOD_NS
        self.trigger_mode = False  # Hardware trigger mode
        self.cam_read_time_us = DEFAULT_CAM_READ_TIME_US
        
        logger.debug(f"SimulatedStrobe initialized (port={device_port}, reply_pause={reply_pause_s}s)")
    
    def packet_read(self) -> Tuple[bool, Optional[int], list]:
        """
        Read packet from SPI (simulated).
        
        Returns:
            (valid, type, data) tuple
        """
        # In simulation, we don't actually read from SPI
        # This would be called by the SPI handler
        return False, None, []
    
    def packet_write(self, type_: int, data: list) -> None:
        """
        Write packet to SPI (simulated).
        
        Processes commands and updates internal state to simulate PIC behavior.
        
        Args:
            type_: Packet type (PACKET_TYPE_* constant)
            data: Packet data bytes
        """
        try:
            if type_ == self.PACKET_TYPE_SET_ENABLE:
                if len(data) >= 1:
                    self.enabled = bool(data[0])
                    logger.debug(f"Strobe enable set to: {self.enabled}")
            elif type_ == self.PACKET_TYPE_SET_TIMING:
                if len(data) >= 8:
                    # Parse wait_ns (4 bytes) and period_ns (4 bytes)
                    self.wait_ns = int.from_bytes(data[0:4], 'little', signed=False)
                    self.period_ns = int.from_bytes(data[4:8], 'little', signed=False)
                    logger.debug(f"Strobe timing: wait={self.wait_ns}ns, period={self.period_ns}ns")
                else:
                    logger.warning(f"SET_TIMING packet too short: {len(data)} bytes")
            elif type_ == self.PACKET_TYPE_SET_HOLD:
                if len(data) >= 1:
                    self.hold = bool(data[0])
                    logger.debug(f"Strobe hold set to: {self.hold}")
            elif type_ == self.PACKET_TYPE_SET_TRIGGER_MODE:
                if len(data) >= 1:
                    self.trigger_mode = bool(data[0])
                    logger.debug(f"Strobe trigger mode set to hardware: {self.trigger_mode}")
            else:
                logger.debug(f"Unhandled packet type: {type_}")
        except (ValueError, IndexError, TypeError) as e:
            logger.error(f"Error processing packet write: {e}")
    
    def packet_query(self, type_: int, data: list) -> Tuple[bool, list]:
        """
        Query device (write + read response).
        
        Simulates the SPI query protocol: write command, wait for reply,
        then return response data.
        
        Args:
            type_: Packet type (PACKET_TYPE_* constant)
            data: Packet data bytes
        
        Returns:
            Tuple of (valid, response_data) where:
            - valid: True if query was successful
            - response_data: Response bytes from simulated device
        """
        # Write command
        self.packet_write(type_, data)
        
        # Simulate reply delay (PIC processing time)
        time.sleep(self.reply_pause_s)
        
        # Generate response based on packet type
        # Note: Real firmware returns [0] for success, then data
        response = []
        valid = True
        
        if type_ == self.PACKET_TYPE_SET_ENABLE:
            # SET_ENABLE: returns [0] for success, then wait_ns (4 bytes), period_ns (4 bytes)
            response = [0]  # Success
            response.extend(list(self.wait_ns.to_bytes(4, 'little', signed=False)))
            response.extend(list(self.period_ns.to_bytes(4, 'little', signed=False)))
        elif type_ == self.PACKET_TYPE_SET_TIMING:
            # SET_TIMING: returns [0] for success, then wait_ns (4 bytes), period_ns (4 bytes)
            response = [0]  # Success
            response.extend(list(self.wait_ns.to_bytes(4, 'little', signed=False)))
            response.extend(list(self.period_ns.to_bytes(4, 'little', signed=False)))
        elif type_ == self.PACKET_TYPE_SET_HOLD:
            # SET_HOLD: returns [0] for success
            response = [0]  # Success
        elif type_ == self.PACKET_TYPE_GET_CAM_READ_TIME:
            # GET_CAM_READ_TIME: returns [0] for success, then cam_read_time_us (2 bytes)
            response = [0]  # Success
            response.extend(list(self.cam_read_time_us.to_bytes(2, 'little', signed=False)))
        elif type_ == self.PACKET_TYPE_SET_TRIGGER_MODE:
            # SET_TRIGGER_MODE: returns [0] for success
            response = [0]  # Success
        else:
            valid = False
            response = []
            logger.warning(f"Unknown packet type in query: {type_}")
        
        if not valid:
            logger.debug(f"Invalid packet query: type={type_}, data_len={len(data)}")
        
        return valid, response
    
    # Convenience methods (matching PiStrobe interface)
    def set_enable(self, enable: bool) -> bool:
        """
        Enable/disable strobe.
        
        Args:
            enable: True to enable strobe, False to disable
        
        Returns:
            True if command was successful, False otherwise
        """
        try:
            # Note: Real firmware returns [0] + wait_ns + period_ns for SET_ENABLE
            valid, data = self.packet_query(self.PACKET_TYPE_SET_ENABLE, [1 if enable else 0])
            success = valid and len(data) > 0 and (data[0] == 0)
            if not success:
                logger.warning(f"Failed to set strobe enable: {enable}")
            return success
        except Exception as e:
            logger.error(f"Error setting strobe enable: {e}")
            return False
    
    def get_enable(self) -> Tuple[bool, bool]:
        """Get enable state."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_ENABLE, [])
        if valid and len(data) >= 1:
            return True, bool(data[0])
        return False, False
    
    def set_timing(self, wait_ns: int, period_ns: int) -> Tuple[bool, int, int]:
        """
        Set strobe timing parameters.
        
        Args:
            wait_ns: Wait time in nanoseconds (delay after trigger before strobe fires)
            period_ns: Strobe pulse period in nanoseconds
        
        Returns:
            Tuple of (valid, actual_wait_ns, actual_period_ns) where:
            - valid: True if command was successful
            - actual_wait_ns: Actual wait time set (may differ from requested)
            - actual_period_ns: Actual period set (may differ from requested)
        """
        try:
            if wait_ns < 0 or period_ns < 0:
                logger.warning(f"Invalid timing values: wait={wait_ns}ns, period={period_ns}ns")
                return False, 0, 0
            
            data = list(wait_ns.to_bytes(4, 'little', signed=False))
            data.extend(list(period_ns.to_bytes(4, 'little', signed=False)))
            valid, response = self.packet_query(self.PACKET_TYPE_SET_TIMING, data)
            
            if valid and len(response) >= 9:
                # Response format: [0] + wait_ns (4 bytes) + period_ns (4 bytes)
                actual_wait_ns = int.from_bytes(response[1:5], 'little', signed=False)
                actual_period_ns = int.from_bytes(response[5:9], 'little', signed=False)
                return True, actual_wait_ns, actual_period_ns
            
            logger.warning(f"Failed to set strobe timing: invalid response")
            return False, 0, 0
        except (ValueError, IndexError, TypeError) as e:
            logger.error(f"Error setting strobe timing: {e}")
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
        """
        Set strobe hold state.
        
        Args:
            hold: True to enable hold mode, False to disable
        
        Returns:
            True if command was successful, False otherwise
        """
        try:
            valid, data = self.packet_query(self.PACKET_TYPE_SET_HOLD, [1 if hold else 0])
            success = valid and len(data) > 0 and (data[0] == 0)
            if not success:
                logger.warning(f"Failed to set strobe hold: {hold}")
            return success
        except Exception as e:
            logger.error(f"Error setting strobe hold: {e}")
            return False
    
    def get_hold(self) -> Tuple[bool, bool]:
        """Get hold state."""
        valid, data = self.packet_query(self.PACKET_TYPE_GET_HOLD, [])
        if valid and len(data) >= 1:
            return True, bool(data[0])
        return False, False
    
    def get_cam_read_time(self) -> Tuple[bool, int]:
        """
        Get camera read time (simulated).
        
        Returns:
            Tuple of (valid, cam_read_time_us) where cam_read_time_us is in microseconds
        """
        valid, data = self.packet_query(self.PACKET_TYPE_GET_CAM_READ_TIME, [])
        # Real firmware returns [0] + cam_read_time_us (2 bytes)
        if valid and len(data) >= 3:
            cam_read_time_us = int.from_bytes(data[1:3], 'little', signed=False)
            return True, cam_read_time_us
        return False, 0
    
    def set_trigger_mode(self, hardware_trigger: bool) -> bool:
        """
        Set trigger mode (hardware vs software).
        
        Args:
            hardware_trigger: True for hardware trigger mode (camera triggers strobe),
                            False for software trigger mode
        
        Returns:
            True if command was successful, False otherwise
        """
        try:
            valid, data = self.packet_query(self.PACKET_TYPE_SET_TRIGGER_MODE, [1 if hardware_trigger else 0])
            success = valid and len(data) > 0 and (data[0] == 0)
            if not success:
                logger.warning(f"Failed to set trigger mode: hardware={hardware_trigger}")
            return success
        except Exception as e:
            logger.error(f"Error setting trigger mode: {e}")
            return False

