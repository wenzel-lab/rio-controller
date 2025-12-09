"""
Simulated SPI and GPIO handler.

Mocks Raspberry Pi SPI and GPIO operations for testing without hardware.
"""

import time
from threading import Lock
from typing import List, Optional


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
    
    _mode = None
    _pins = {}  # pin_number -> {'mode': mode, 'value': value, 'pull': pull}
    
    @classmethod
    def setmode(cls, mode):
        """Set GPIO numbering mode."""
        cls._mode = mode
        print(f"[SimulatedGPIO] Mode set to {mode}")
    
    @classmethod
    def setup(cls, channel, direction, initial=None, pull_up_down=None):
        """Setup GPIO pin."""
        if channel not in cls._pins:
            cls._pins[channel] = {}
        
        cls._pins[channel]['mode'] = direction
        if initial is not None:
            cls._pins[channel]['value'] = initial
        else:
            cls._pins[channel]['value'] = cls.LOW
        if pull_up_down is not None:
            cls._pins[channel]['pull'] = pull_up_down
        
        print(f"[SimulatedGPIO] Pin {channel} setup: mode={direction}, initial={initial}")
    
    @classmethod
    def output(cls, channel, value):
        """Set GPIO output."""
        if channel in cls._pins:
            cls._pins[channel]['value'] = value
            print(f"[SimulatedGPIO] Pin {channel} = {value}")
        else:
            print(f"[SimulatedGPIO] Warning: Pin {channel} not configured")
    
    @classmethod
    def input(cls, channel):
        """Read GPIO input."""
        if channel in cls._pins:
            return cls._pins[channel].get('value', cls.LOW)
        return cls.LOW
    
    @classmethod
    def cleanup(cls):
        """Cleanup GPIO."""
        cls._pins.clear()
        print("[SimulatedGPIO] Cleaned up")


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
        print(f"[SimulatedSPI] Opened bus={bus}, device={device}")
    
    def xfer2(self, data: List[int]) -> List[int]:
        """
        Transfer data (simulated).
        
        In simulation mode, this logs the transfer and returns
        a mock response based on the device being addressed.
        """
        self._transfers.append(data.copy())
        
        # Mock response: echo back data (typical for testing)
        # Real implementations would return device-specific responses
        response = [0] * len(data)
        
        # If this looks like a strobe command, return mock strobe response
        if len(data) >= 3 and data[0] == 2:  # STX byte
            # Mock valid response
            response = [2, len(data), data[2]] + [0] * (len(data) - 4) + [0]  # Valid checksum
        
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
    """
    
    def __init__(self, bus: int = 0, mode: int = 2, speed_hz: int = 30000, pin_mode=None):
        """
        Initialize simulated SPI handler.
        
        Args:
            bus: SPI bus number (simulated)
            mode: SPI mode (simulated)
            speed_hz: SPI speed (simulated)
            pin_mode: GPIO pin mode (GPIO.BOARD or GPIO.BCM)
        """
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
        
        print(f"[SimulatedSPIHandler] Initialized (bus={bus}, mode={mode}, speed={speed_hz}Hz)")
    
    def initialize_port(self, port_number: int, mode: int, initial: Optional[int] = None, 
                       pull_up_down: int = 20):
        """Initialize GPIO port."""
        self.GPIO.setup(port_number, mode, initial=initial, pull_up_down=pull_up_down)
    
    def spi_select_device(self, device: Optional[int]):
        """Select SPI device (simulated)."""
        if (self.current_device is not None) and (device != self.current_device):
            self.GPIO.output(self.current_device, self.GPIO.HIGH)
            self.current_device = None
        
        if (device is not None) and (device != self.current_device):
            self.GPIO.output(device, self.GPIO.LOW)
            self.current_device = device
    
    def spi_deselect_current(self):
        """Deselect current SPI device."""
        if self.current_device is not None:
            self.GPIO.output(self.current_device, self.GPIO.HIGH)
            self.current_device = None
    
    def spi_lock(self):
        """Acquire SPI lock."""
        self.pi_lock.acquire()
    
    def spi_release(self):
        """Release SPI lock."""
        self.pi_lock.release()
    
    def pi_wait_s(self, seconds: float):
        """Wait (simulated - uses real time.sleep)."""
        time.sleep(seconds)
    
    def read_bytes(self, bytes_: int) -> List[int]:
        """
        Read bytes from SPI (simulated).
        
        Returns mock data (zeros by default).
        """
        data = []
        for _ in range(bytes_):
            data.extend(self.spi.xfer2([0]))
        return data

