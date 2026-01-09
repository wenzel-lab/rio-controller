import os
import time
from threading import Lock

# Check if we're in simulation mode
SIMULATION_MODE = os.getenv("RIO_SIMULATION", "false").lower() == "true"

if SIMULATION_MODE:
    # Use simulated SPI and GPIO
    try:
        from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO

        GPIO = SimulatedGPIO
        # Create simulated SPI handler (will be initialized later)
        _simulated_spi_handler = None
    except ImportError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Could not import simulation module: {e}")
        raise
else:
    # Use real hardware
    try:
        import spidev
        import RPi.GPIO as GPIO  # type: ignore[no-redef]
    except ImportError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Hardware libraries not available ({e}). Enable simulation mode with RIO_SIMULATION=true"
        )
        raise

PORT_NONE = 0
PORT_HEATER1 = 31
PORT_HEATER2 = 33
PORT_HEATER3 = 32
PORT_HEATER4 = 36
PORT_STROBE = 24
PORT_FLOW = 26

col_lightgray1 = "#C0C0C0"
col_lightgray2 = "#E0E0E0"

# Global variables for SPI state (module-level, accessible as spi_handler.spi)
current_device = PORT_NONE
pi_lock = Lock()
spi = None  # Initialize to None - will be set by spi_init()


def spi_init(bus, mode, speed_hz):
    global spi
    global current_device
    global _simulated_spi_handler

    if SIMULATION_MODE:
        # Use simulated SPI handler
        _simulated_spi_handler = SimulatedSPIHandler(
            bus=bus, mode=mode, speed_hz=speed_hz, pin_mode=GPIO.BOARD
        )
        spi = (
            _simulated_spi_handler.spi
        )  # Access the simulated SPI device - this assigns to global spi

        # Initialize GPIO ports (simulated)
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        _simulated_spi_handler.initialize_port(PORT_HEATER1, GPIO.OUT, initial=GPIO.HIGH)
        _simulated_spi_handler.initialize_port(PORT_HEATER2, GPIO.OUT, initial=GPIO.HIGH)
        _simulated_spi_handler.initialize_port(PORT_HEATER3, GPIO.OUT, initial=GPIO.HIGH)
        _simulated_spi_handler.initialize_port(PORT_HEATER4, GPIO.OUT, initial=GPIO.HIGH)
        _simulated_spi_handler.initialize_port(PORT_STROBE, GPIO.OUT, initial=GPIO.HIGH)
        _simulated_spi_handler.initialize_port(PORT_FLOW, GPIO.OUT, initial=GPIO.HIGH)

        import logging

        logger = logging.getLogger(__name__)
        logger.info("Using simulated SPI/GPIO (simulation mode)")
    else:
        # Use real hardware
        spi = spidev.SpiDev()
        spi.open(bus, 0)
        spi.mode = mode
        spi.max_speed_hz = speed_hz
        spi.no_cs = True

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(PORT_HEATER1, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(PORT_HEATER2, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(PORT_HEATER3, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(PORT_HEATER4, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(PORT_STROBE, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(PORT_FLOW, GPIO.OUT, initial=GPIO.HIGH)

    current_device = PORT_NONE

    return spi


def spi_close() -> None:
    if SIMULATION_MODE and _simulated_spi_handler and _simulated_spi_handler.spi:
        _simulated_spi_handler.spi.close()
    elif not SIMULATION_MODE and spi:
        spi.close()


def spi_select_device(device):
    global current_device

    if SIMULATION_MODE and _simulated_spi_handler:
        _simulated_spi_handler.spi_select_device(device)
        current_device = device
    else:
        if (current_device != PORT_NONE) and (device != current_device):
            GPIO.output(current_device, GPIO.HIGH)
            # print( "Dropped {}".format( current_device ) )
            current_device = PORT_NONE
            # time.sleep(0.1)

        if (device != PORT_NONE) and (device != current_device):
            GPIO.output(device, GPIO.LOW)
            current_device = device
            # print( "Selected {}".format( current_device ) )


def spi_deselect_current():
    global current_device

    if SIMULATION_MODE and _simulated_spi_handler:
        _simulated_spi_handler.spi_deselect_current()
        current_device = PORT_NONE
    else:
        if current_device != PORT_NONE:
            GPIO.output(current_device, GPIO.HIGH)
            # print( "Deselected {}".format( current_device ) )
            current_device = PORT_NONE
            # time.sleep(0.1)


def spi_lock():
    if SIMULATION_MODE and _simulated_spi_handler:
        _simulated_spi_handler.spi_lock()
    else:
        pi_lock.acquire()


#  while not pi_lock.acquire( False ):
#    pass


def spi_release():

    if SIMULATION_MODE and _simulated_spi_handler:
        _simulated_spi_handler.spi_release()
    else:
        pi_lock.release()


def pi_wait_s(delay_s):
    start_time = time.time()
    while (time.time() - start_time) < delay_s:
        pass
