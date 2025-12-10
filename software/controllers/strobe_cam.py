"""
Strobe-camera integration module.

This module provides the PiStrobeCam class which integrates camera control
with strobe timing synchronization. It handles hardware-triggered strobe
operation where the camera frame callback triggers the PIC microcontroller
via GPIO.

Classes:
    PiStrobeCam: Integrates camera and strobe for synchronized operation
"""

import time
import sys
import os
import logging
from typing import Optional, Tuple, Any, cast

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.strobe import PiStrobe  # noqa: E402
from drivers.spi_handler import GPIO  # noqa: E402  # Handles simulation mode automatically
from drivers.camera import create_camera, BaseCamera  # noqa: E402

# Import configuration constants
try:
    # Config is now at software/ level (same level as controllers/)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import (
        CAMERA_DEFAULT_WIDTH,
        CAMERA_DEFAULT_HEIGHT,
        CAMERA_DEFAULT_FPS,
        STROBE_TRIGGER_GPIO_PIN,
        STROBE_TRIGGER_PULSE_US,
        STROBE_REPLY_PAUSE_S,
        STROBE_PRE_PADDING_NS,
        STROBE_POST_PADDING_NS,
    )
except ImportError:
    # Fallback values if config module not available
    CAMERA_DEFAULT_WIDTH = 640
    CAMERA_DEFAULT_HEIGHT = 480
    CAMERA_DEFAULT_FPS = 30
    STROBE_TRIGGER_GPIO_PIN = 18
    STROBE_TRIGGER_PULSE_US = 0.000001
    STROBE_REPLY_PAUSE_S = 0.1
    STROBE_PRE_PADDING_NS = 32
    STROBE_POST_PADDING_NS = 20000000

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_FRAMERATE = 60  # Maximum framerate in FPS
NS_TO_US = 1000  # Nanoseconds to microseconds conversion
US_TO_NS = 1000  # Microseconds to nanoseconds conversion


class PiStrobeCam:
    """
    Camera-strobe integration controller.

    This class integrates camera control with strobe timing synchronization.
    It uses hardware-triggered mode where the camera frame callback triggers
    the PIC microcontroller via GPIO, allowing precise strobe timing.

    Attributes:
        strobe: PiStrobe instance for strobe hardware control
        camera: Camera abstraction layer instance
        trigger_gpio_pin: GPIO pin number for PIC trigger signal
        strobe_wait_ns: Strobe wait time in nanoseconds
        strobe_period_ns: Strobe pulse period in nanoseconds
        framerate_set: Configured framerate in FPS
    """

    def __init__(
        self,
        port: int,
        reply_pause_s: float = STROBE_REPLY_PAUSE_S,
        trigger_gpio_pin: int = STROBE_TRIGGER_GPIO_PIN,
    ) -> None:
        """
        Initialize the PiStrobeCam controller.

        Args:
            port: GPIO port number for SPI device selection
            reply_pause_s: SPI reply pause time in seconds
            trigger_gpio_pin: GPIO pin number for PIC trigger (BCM numbering)
        """
        logger.info(f"Initializing PiStrobeCam (port={port}, trigger_pin={trigger_gpio_pin})")

        # Initialize strobe controller
        self.strobe = PiStrobe(port, reply_pause_s)
        self.trigger_gpio_pin = trigger_gpio_pin

        # Initialize camera using abstraction layer (will be created when camera type is selected)
        # Create default camera (rpi) for initialization
        try:
            camera_instance = create_camera()
            self.camera: Optional[BaseCamera] = (
                camera_instance if camera_instance is not None else None
            )
            self._camera_type: Optional[str] = "rpi" if camera_instance is not None else None

            # Configure camera with default settings
            if self.camera is not None:
                self.camera.set_config(
                    {
                        "Width": CAMERA_DEFAULT_WIDTH,
                        "Height": CAMERA_DEFAULT_HEIGHT,
                        "FrameRate": CAMERA_DEFAULT_FPS,
                    }
                )
        except Exception as e:
            logger.error(f"Error creating/configuring camera: {e}")
            # In simulation mode, this should work, so raise
            raise

        # Initialize GPIO for PIC trigger (software-triggered mode)
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trigger_gpio_pin, GPIO.OUT)
            GPIO.output(self.trigger_gpio_pin, GPIO.LOW)
            logger.debug(f"GPIO pin {self.trigger_gpio_pin} configured for trigger")
        except Exception as e:
            logger.error(f"Error configuring GPIO trigger pin: {e}")
            raise

        # Configure strobe for hardware trigger mode (PIC waits for GPIO trigger)
        try:
            self.strobe.set_trigger_mode(True)  # Hardware trigger mode
            logger.debug("Strobe configured for hardware trigger mode")
        except Exception as e:
            logger.error(f"Error configuring strobe trigger mode: {e}")
            raise

        # Set frame callback for strobe trigger (if camera is initialized)
        if self.camera:
            self.camera.set_frame_callback(self.frame_callback_trigger)

        # Initialize timing state
        self.strobe_wait_ns = 0
        self.strobe_period_ns = 0
        self.framerate_set = 0

        logger.info("PiStrobeCam initialization complete")

    def set_camera_type(self, camera_type: str) -> bool:
        """
        Set camera type and create appropriate camera instance.

        Args:
            camera_type: Camera type ('none', 'rpi', 'rpi_hq', 'mako')

        Returns:
            True if camera was created successfully, False otherwise
        """
        try:
            # Close existing camera if any
            if self.camera:
                try:
                    self.camera.close()
                except Exception:
                    pass
                self.camera = None

            if camera_type == "none":
                self._camera_type = None
                logger.info("Camera set to 'none'")
                return True

            # Create new camera instance
            from drivers.camera import create_camera

            new_camera = create_camera(camera_type=camera_type)
            if new_camera is not None:
                self.camera = new_camera
                self._camera_type = camera_type
            else:
                self.camera = None
                self._camera_type = None

            # Configure camera with default settings
            if self.camera is not None:
                self.camera.set_config(
                    {
                        "Width": CAMERA_DEFAULT_WIDTH,
                        "Height": CAMERA_DEFAULT_HEIGHT,
                        "FrameRate": CAMERA_DEFAULT_FPS,
                    }
                )

                # Set frame callback for strobe trigger
                self.camera.set_frame_callback(self.frame_callback_trigger)

            logger.info(f"Camera type set to: {camera_type}")
            return True
        except Exception as e:
            logger.error(f"Error setting camera type to {camera_type}: {e}")
            self.camera = None
            self._camera_type = None
            return False

    def frame_callback_trigger(self) -> None:
        """
        Frame callback - triggers PIC via GPIO pin.

        This method is called on each frame capture by the camera. It generates
        a short pulse on the GPIO pin to trigger the PIC microcontroller.
        Note: Software callback has ~1-5ms jitter, but PIC hardware timing
        remains precise.
        """
        try:
            # Generate short pulse to PIC T1G input (hardware trigger)
            GPIO.output(self.trigger_gpio_pin, GPIO.HIGH)
            time.sleep(STROBE_TRIGGER_PULSE_US)  # 1us pulse (PIC detects edge)
            GPIO.output(self.trigger_gpio_pin, GPIO.LOW)
        except Exception as e:
            logger.error(f"Error in frame callback trigger: {e}")

    def set_timing(self, pre_padding_ns: int, strobe_period_ns: int, post_padding_ns: int) -> bool:
        """
        Set strobe timing parameters.

        For hardware trigger mode, timing is simpler:
        - Camera runs at configured framerate
        - Frame callback triggers PIC via GPIO
        - PIC generates strobe pulse with specified timing

        Args:
            pre_padding_ns: Delay after trigger before strobe fires (nanoseconds)
            strobe_period_ns: Strobe pulse duration (nanoseconds)
            post_padding_ns: Post-padding time after strobe (nanoseconds)

        Returns:
            True if timing was set successfully, False otherwise
        """
        try:
            if not self._set_strobe_timing(pre_padding_ns, strobe_period_ns):
                return False

            framerate, shutter_speed_us = self._calculate_camera_timing(
                strobe_period_ns, pre_padding_ns, post_padding_ns
            )

            if not self._update_camera_config(framerate, shutter_speed_us):
                return False

            if not self._ensure_camera_started():
                return False

            self.framerate_set = framerate
            logger.debug(
                f"Strobe timing set: period={strobe_period_ns}ns, "
                f"framerate={framerate}fps, shutter={shutter_speed_us}us"
            )
            return True
        except Exception as e:
            logger.error(f"Error in set_timing: {e}")
            return False

    def _set_strobe_timing(self, pre_padding_ns: int, strobe_period_ns: int) -> bool:
        """Set strobe timing on hardware."""
        wait_ns = pre_padding_ns
        valid, self.strobe_wait_ns, self.strobe_period_ns = self.strobe.set_timing(
            wait_ns, strobe_period_ns
        )
        if not valid:
            logger.warning("Failed to set strobe timing")
        return cast(bool, valid)

    def _calculate_camera_timing(
        self, strobe_period_ns: int, pre_padding_ns: int, post_padding_ns: int
    ) -> tuple[int, int]:
        """Calculate camera framerate and shutter speed from strobe timing."""
        total_exposure_ns = strobe_period_ns + pre_padding_ns + post_padding_ns
        shutter_speed_us = int(total_exposure_ns / NS_TO_US)
        framerate = int(1000000 / shutter_speed_us)

        if framerate > MAX_FRAMERATE:
            framerate = MAX_FRAMERATE
            logger.warning(f"Framerate clamped to {MAX_FRAMERATE} FPS")

        return framerate, shutter_speed_us

    def _update_camera_config(self, framerate: int, shutter_speed_us: int) -> bool:
        """Update camera configuration."""
        if self.camera is None:
            logger.error("Camera is None, cannot update config")
            return False
        try:
            self.camera.set_config({"FrameRate": framerate, "ShutterSpeed": shutter_speed_us})
            return True
        except Exception as e:
            logger.error(f"Error setting camera config: {e}")
            return False

    def _ensure_camera_started(self) -> bool:
        """Ensure camera is started and strobe is enabled."""
        if self.camera is None:
            logger.error("Camera is None, cannot start")
            return False
        try:
            self.camera.start()
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False

        try:
            self.strobe.set_enable(True)
        except Exception as e:
            logger.error(f"Error enabling strobe: {e}")
            return False

        return True

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> Optional[Any]:
        """
        Get ROI (Region of Interest) frame for droplet detection.

        Args:
            roi: Tuple of (x, y, width, height) defining the ROI

        Returns:
            numpy.ndarray: ROI frame as numpy array, or None if unavailable
        """
        try:
            if self.camera is None:
                return None
            return self.camera.get_frame_roi(roi)
        except Exception as e:
            logger.error(f"Error getting ROI frame: {e}")
            return None

    def close(self) -> None:
        """
        Close camera and disable strobe.

        Properly shuts down the camera and strobe, ensuring all resources
        are released.
        """
        try:
            self.strobe.set_enable(False)
            self.strobe.set_hold(False)
            if self.camera:
                self.camera.close()
            logger.info("PiStrobeCam closed")
        except Exception as e:
            logger.error(f"Error closing PiStrobeCam: {e}")
