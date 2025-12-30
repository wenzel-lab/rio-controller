"""
Simulated SPI and GPIO handler.

Mocks Raspberry Pi SPI and GPIO operations for testing without hardware.
This module provides drop-in replacements for RPi.GPIO and spidev,
allowing the application to run and be tested on any system.

Classes:
    SimulatedGPIO: GPIO module replacement
    SimulatedSPIDev: SPI device replacement
    SimulatedSPIHandler: SPI handler replacement
"""

import time
import logging
from threading import Lock
from typing import List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_BUS = 0
DEFAULT_MODE = 2
DEFAULT_SPEED_HZ = 30000


class SimulatedGPIO:
    """Mock GPIO module (replaces RPi.GPIO)."""

    # GPIO constants
    BOARD = 10
    BCM = 11
    OUT = 0
    IN = 1
    LOW = 0
    HIGH = 1
    PUD_UP = 22
    PUD_DOWN = 21

    _mode: Optional[int] = None
    _pins: dict[int, dict[str, int]] = (
        {}
    )  # pin_number -> {'mode': mode, 'value': value, 'pull': pull}

    @classmethod
    def setmode(cls, mode: int) -> None:
        """
        Set GPIO numbering mode.

        Args:
            mode: GPIO.BOARD or GPIO.BCM
        """
        if mode not in (cls.BOARD, cls.BCM):
            logger.warning(f"Invalid GPIO mode: {mode}")
        cls._mode = mode
        logger.debug(f"GPIO mode set to: {mode}")

    @classmethod
    def setup(
        cls,
        channel: int,
        direction: int,
        initial: Optional[int] = None,
        pull_up_down: Optional[int] = None,
    ) -> None:
        """
        Setup GPIO pin.

        Args:
            channel: GPIO pin number
            direction: GPIO.IN or GPIO.OUT
            initial: Initial value (for OUTPUT mode)
            pull_up_down: Pull-up/down configuration (for INPUT mode)
        """
        if channel < 0:
            logger.warning(f"Invalid GPIO channel: {channel}")
            return

        if channel not in cls._pins:
            cls._pins[channel] = {}

        cls._pins[channel]["mode"] = direction
        if initial is not None:
            cls._pins[channel]["value"] = initial
        else:
            cls._pins[channel]["value"] = cls.LOW
        if pull_up_down is not None:
            cls._pins[channel]["pull"] = pull_up_down

        logger.debug(f"GPIO pin {channel} setup: mode={direction}, initial={initial}")

    @classmethod
    def output(cls, channel: int, value: int) -> None:
        """
        Set GPIO output value.

        Args:
            channel: GPIO pin number
            value: GPIO.LOW (0) or GPIO.HIGH (1)
        """
        if channel not in cls._pins:
            logger.warning(f"GPIO pin {channel} not configured, cannot set output")
            return

        if cls._pins[channel].get("mode") != cls.OUT:
            logger.warning(f"GPIO pin {channel} is not configured as OUTPUT")
            return

        cls._pins[channel]["value"] = value
        logger.debug(f"GPIO pin {channel} set to: {value}")

    @classmethod
    def input(cls, channel: int) -> int:
        """
        Read GPIO input value.

        Args:
            channel: GPIO pin number

        Returns:
            GPIO.LOW (0) or GPIO.HIGH (1)
        """
        if channel not in cls._pins:
            logger.warning(f"GPIO pin {channel} not configured, returning LOW")
            return cls.LOW

        pin_data = cls._pins.get(channel, {})
        return int(pin_data.get("value", cls.LOW))

    @classmethod
    def setwarnings(cls, enable: bool) -> None:
        """
        Set GPIO warnings (simulated - does nothing but matches RPi.GPIO interface).

        Args:
            enable: True to enable warnings, False to disable
        """
        # In simulation, warnings don't matter, but we need this method for compatibility
        logger.debug(f"GPIO warnings set to: {enable}")

    @classmethod
    def cleanup(cls) -> None:
        """
        Cleanup GPIO resources.

        Clears all pin configurations. Should be called on application shutdown.
        """
        cls._pins.clear()
        logger.info("SimulatedGPIO cleaned up")


class SimulatedSPIDev:
    """Mock SPI device (replaces spidev.SpiDev)."""

    def __init__(self, handler=None):
        self.bus = None
        self.device = None
        self.mode = 0
        self.max_speed_hz = 0
        self._transfers = []  # Log of all transfers
        self._handler = handler  # Reference to SimulatedSPIHandler for routing

    def open(self, bus, device):
        """Open SPI device."""
        self.bus = bus
        self.device = device

    def xfer2(self, data: List[int]) -> List[int]:
        """
        Transfer data (simulated).

        Routes packets to appropriate simulated device based on selected port.
        """
        self._transfers.append(data.copy())

        # If no handler, return mock response (shouldn't happen)
        if self._handler is None:
            return [0] * len(data)

        # Check if this is a read request (single zero byte)
        if len(data) == 1 and data[0] == 0:
            # Read operation - return stored response from handler
            return self._handler.get_stored_response()

        # Check if this is a packet (STX byte = 2)
        if len(data) >= 3 and data[0] == 2:  # STX byte
            # Route packet through handler
            response = self._handler.route_packet(data)
            return response

        # Default: echo data back
        return data

    def close(self):
        """Close SPI device."""
        print(f"[SimulatedSPI] Closed bus={self.bus}, device={self.device}")
        self.bus = None
        self.device = None


class SimulatedSPIHandler:
    """
    Simulated SPI handler (replaces real SPIHandler).

    Provides same interface as flow-microscopy-platform SPIHandler
    but without requiring actual hardware.

    Routes SPI transfers to appropriate simulated devices (flow, strobe, heater).
    """

    def __init__(
        self,
        bus: int = DEFAULT_BUS,
        mode: int = DEFAULT_MODE,
        speed_hz: int = DEFAULT_SPEED_HZ,
        pin_mode: Optional[int] = None,
    ):
        """
        Initialize simulated SPI handler.

        Args:
            bus: SPI bus number (simulated, default: 0)
            mode: SPI mode (simulated, default: 2)
            speed_hz: SPI speed in Hz (simulated, default: 30000)
            pin_mode: GPIO pin mode - GPIO.BOARD or GPIO.BCM (default: BCM)

        Raises:
            ValueError: If bus, mode, or speed_hz are invalid
        """
        if bus < 0:
            raise ValueError(f"Invalid SPI bus: {bus}")
        if mode < 0 or mode > 3:
            raise ValueError(f"Invalid SPI mode: {mode}")
        if speed_hz <= 0:
            raise ValueError(f"Invalid SPI speed: {speed_hz}")

        self.spi = SimulatedSPIDev()
        self.spi.open(bus, 0)
        self.spi.mode = mode
        self.spi.max_speed_hz = speed_hz

        # Use simulated GPIO
        self.GPIO = SimulatedGPIO
        if pin_mode is None:
            pin_mode = SimulatedGPIO.BCM
        self.GPIO.setmode(pin_mode)

        self.current_device: Optional[int] = None
        self.pi_lock = Lock()

        # Simulated devices (lazy initialization)
        self._simulated_flow = None
        self._simulated_strobe = None
        self._simulated_heaters: dict[int, Any] = {}  # port -> heater instance

        # Store last response for read operations
        self._stored_response: List[int] = []

        # Create SPI device with handler reference
        self.spi = SimulatedSPIDev(handler=self)
        self.spi.open(bus, 0)
        self.spi.mode = mode
        self.spi.max_speed_hz = speed_hz

        logger.info(f"SimulatedSPIHandler initialized (bus={bus}, mode={mode}, speed={speed_hz}Hz)")

    def initialize_port(
        self, port_number: int, mode: int, initial: Optional[int] = None, pull_up_down: int = 20
    ) -> None:
        """
        Initialize GPIO port.

        Args:
            port_number: GPIO port number
            mode: GPIO.IN or GPIO.OUT
            initial: Initial value (for OUTPUT mode)
            pull_up_down: Pull-up/down configuration (for INPUT mode)
        """
        try:
            self.GPIO.setup(port_number, mode, initial=initial, pull_up_down=pull_up_down)
        except Exception as e:
            logger.error(f"Error initializing GPIO port {port_number}: {e}")

    def spi_select_device(self, device: Optional[int]) -> None:
        """
        Select SPI device (simulated).

        Args:
            device: Device port number to select, or None to deselect all
        """
        try:
            if (self.current_device is not None) and (device != self.current_device):
                self.GPIO.output(self.current_device, self.GPIO.HIGH)
                self.current_device = None

            if (device is not None) and (device != self.current_device):
                self.GPIO.output(device, self.GPIO.LOW)
                self.current_device = device
                logger.debug(f"SPI device selected: {device}")
        except Exception as e:
            logger.error(f"Error selecting SPI device {device}: {e}")

    def spi_deselect_current(self) -> None:
        """
        Deselect current SPI device.

        Sets the current device's CS line high and clears the current device.
        """
        try:
            if self.current_device is not None:
                self.GPIO.output(self.current_device, self.GPIO.HIGH)
                self.current_device = None
                logger.debug("SPI device deselected")
        except Exception as e:
            logger.error(f"Error deselecting SPI device: {e}")

    def spi_lock(self) -> None:
        """
        Acquire SPI lock.

        Thread-safe access to SPI bus. Blocks until lock is available.
        """
        self.pi_lock.acquire()
        logger.debug("SPI lock acquired")

    def spi_release(self) -> None:
        """
        Release SPI lock.

        Releases the SPI bus lock, allowing other threads to access it.
        """
        try:
            if self.pi_lock.locked():
                self.pi_lock.release()
                logger.debug("SPI lock released")
        except Exception as e:
            logger.error(f"Error releasing SPI lock: {e}")

    def pi_wait_s(self, seconds: float) -> None:
        """
        Wait for specified time (simulated - uses real time.sleep).

        Args:
            seconds: Time to wait in seconds
        """
        if seconds < 0:
            logger.warning(f"Invalid wait time: {seconds}s")
            return
        time.sleep(seconds)

    def read_bytes(self, bytes_: int) -> List[int]:
        """
        Read bytes from SPI (simulated).

        Args:
            bytes_: Number of bytes to read

        Returns:
            List of bytes (mock data, zeros by default)

        Raises:
            ValueError: If bytes_ is invalid
        """
        if bytes_ < 0:
            raise ValueError(f"Invalid number of bytes: {bytes_}")

        data = []
        for _ in range(bytes_):
            data.extend(self.spi.xfer2([0]))
        return data

    def get_stored_response(self) -> List[int]:
        """
        Get stored response from last packet operation.

        Returns:
            Stored response bytes, or [0] if no response stored
        """
        if self._stored_response:
            # Return one byte at a time (SPI read behavior)
            if len(self._stored_response) > 0:
                byte = self._stored_response.pop(0)
                return [byte]
        # Return 0 if no response (PIC not ready)
        return [0]

    def route_packet(self, packet: List[int]) -> List[int]:
        """
        Route SPI packet to appropriate simulated device.

        Args:
            packet: SPI packet bytes [STX, size, type, ...data, checksum]

        Returns:
            Response packet bytes (empty for write, will be read later)
        """
        if len(packet) < 3:
            self._stored_response = []
            return []

        # Extract packet components
        stx = packet[0]
        if stx != 2:  # STX byte
            self._stored_response = []
            return []

        size = packet[1] if len(packet) > 1 else 0
        packet_type = packet[2] if len(packet) > 2 else 0
        data = packet[3:-1] if len(packet) > 4 else []  # Skip STX, size, type, checksum

        # Route to appropriate device based on current_device
        response_data = []
        valid = False

        try:
            if self.current_device == 24:  # PORT_STROBE
                if self._simulated_strobe is None:
                    from simulation.strobe_simulated import SimulatedStrobe
                    self._simulated_strobe = SimulatedStrobe(device_port=24, reply_pause_s=0.1)
                valid, response_data = self._simulated_strobe.packet_query(packet_type, data)

            elif self.current_device == 26:  # PORT_FLOW
                if self._simulated_flow is None:
                    from simulation.flow_simulated import SimulatedFlow
                    self._simulated_flow = SimulatedFlow(device_port=26, reply_pause_s=0.1)
                valid, response_data = self._simulated_flow.packet_query(packet_type, data)

            elif self.current_device in [31, 33, 32, 36]:  # PORT_HEATER1-4
                port = self.current_device
                if port not in self._simulated_heaters:
                    from simulation.heater_simulated import SimulatedHeater
                    self._simulated_heaters[port] = SimulatedHeater(device_port=port, reply_pause_s=0.05)
                valid, response_data = self._simulated_heaters[port].packet_query(packet_type, data)

            else:
                logger.warning(f"No simulated device for port {self.current_device}")
                valid = False
                response_data = []

        except Exception as e:
            logger.error(f"Error routing packet to device {self.current_device}: {e}")
            valid = False
            response_data = []

        # Format response packet: [STX, size, type, ...data, checksum]
        if valid and response_data:
            response = [2]  # STX
            response.append(len(response_data) + 4)  # size (type + data + checksum)
            response.append(packet_type)  # echo packet type
            response.extend(response_data)
            # Calculate checksum
            checksum = (-(sum(response) & 0xFF)) & 0xFF
            response.append(checksum)
            # Store response for read operations (packet_read will read this)
            self._stored_response = response.copy()
            # Return empty for write operation (response will be read via xfer2([0]))
            return []
        else:
            # Invalid response - store error packet
            error_response = [2, 4, packet_type, 0xFF, 0]  # STX, size, type, error, checksum
            checksum = (-(sum(error_response) & 0xFF)) & 0xFF
            error_response[-1] = checksum
            self._stored_response = error_response.copy()
            return []
