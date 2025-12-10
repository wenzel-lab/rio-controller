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

    def __init__(self):
        self.bus = None
        self.device = None
        self.mode = 0
        self.max_speed_hz = 0
        self._transfers = []  # Log of all transfers

    def open(self, bus, device):
        """Open SPI device."""
        self.bus = bus
        self.device = device
        # Silent in simulation (too verbose)
        # Uncomment for debugging: print(f"[SimulatedSPI] Opened bus={bus}, device={device}")

    def xfer2(self, data: List[int]) -> List[int]:
        """
        Transfer data (simulated).

        Routes packets to appropriate simulated device based on selected port.
        """
        self._transfers.append(data.copy())

        # Get the current selected device from the handler
        # We need to access the handler's current_device
        # For now, return a mock response - the handler will route this
        response = [0] * len(data)

        # If this looks like a packet (STX byte = 2), try to route it
        if len(data) >= 3 and data[0] == 2:  # STX byte
            # Extract packet type
            if len(data) >= 3:
                packet_type = data[2]
                # Return a basic response - actual routing happens in handler
                response = [2, len(data), packet_type] + [0] * (len(data) - 4) + [0]

        return response

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
