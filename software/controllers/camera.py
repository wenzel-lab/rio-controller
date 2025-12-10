"""
Camera management module for the Rio microfluidics controller.

This module provides the Camera class which integrates the Pi camera with strobe
control, ROI selection, and WebSocket communication for the web interface.

Classes:
    Camera: Main camera controller with strobe synchronization and ROI support
"""

import io
import threading
import time
import logging
import sys
import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from PIL import Image

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.spi_handler import PORT_STROBE  # noqa: E402
from controllers.strobe_cam import PiStrobeCam  # noqa: E402

# Import configuration constants
try:
    # Config is now at software/ level (same level as controllers/)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import (
        CAMERA_THREAD_WIDTH,
        CAMERA_THREAD_HEIGHT,
        CAMERA_THREAD_FPS,
        CAMERA_INIT_TIMEOUT_S,
        CAMERA_FRAME_WAIT_SLEEP_S,
        STROBE_DEFAULT_PERIOD_NS,
        STROBE_MAX_PERIOD_NS,
        STROBE_PRE_PADDING_NS,
        STROBE_POST_PADDING_NS,
        STROBE_REPLY_PAUSE_S,
        CAMERA_TYPE_NONE,
        CAMERA_TYPE_RPI,
        SNAPSHOT_FOLDER,
        SNAPSHOT_FILENAME_PREFIX,
        SNAPSHOT_FILENAME_SUFFIX,
        FPS_OPTIMIZATION_MAX_TRIES,
        FPS_OPTIMIZATION_CONVERGENCE_THRESHOLD_US,
        FPS_OPTIMIZATION_POST_PADDING_OFFSET_US,
        WS_EVENT_CAM,
        WS_EVENT_STROBE,
        WS_EVENT_ROI,
        CMD_SNAPSHOT,
        CMD_OPTIMIZE,
        CMD_HOLD,
        CMD_ENABLE,
        CMD_TIMING,
        CMD_SET,
        CMD_GET,
        CMD_CLEAR,
    )
except ImportError:
    # Fallback values if config module not available
    CAMERA_THREAD_WIDTH = 1024
    CAMERA_THREAD_HEIGHT = 768
    CAMERA_THREAD_FPS = 30
    CAMERA_INIT_TIMEOUT_S = 5.0
    CAMERA_FRAME_WAIT_SLEEP_S = 0.01
    STROBE_DEFAULT_PERIOD_NS = 100000
    STROBE_MAX_PERIOD_NS = 16000000
    STROBE_PRE_PADDING_NS = 32
    STROBE_POST_PADDING_NS = 20000000
    STROBE_REPLY_PAUSE_S = 0.1
    CAMERA_TYPE_NONE = "none"
    CAMERA_TYPE_RPI = "rpi"
    SNAPSHOT_FOLDER = "home/pi/snapshots/"
    SNAPSHOT_FILENAME_PREFIX = "snapshot_"
    SNAPSHOT_FILENAME_SUFFIX = ".jpg"
    FPS_OPTIMIZATION_MAX_TRIES = 10
    FPS_OPTIMIZATION_CONVERGENCE_THRESHOLD_US = 1000
    FPS_OPTIMIZATION_POST_PADDING_OFFSET_US = 100
    WS_EVENT_CAM = "cam"
    WS_EVENT_STROBE = "strobe"
    WS_EVENT_ROI = "roi"
    CMD_SNAPSHOT = "snapshot"
    CMD_OPTIMIZE = "optimize"
    CMD_HOLD = "hold"
    CMD_ENABLE = "enable"
    CMD_TIMING = "timing"
    CMD_SET = "set"
    CMD_GET = "get"
    CMD_CLEAR = "clear"

# Configure logging
logger = logging.getLogger(__name__)


class Camera:
    """
    Camera controller with strobe synchronization and ROI support.

    This class manages the camera feed, strobe timing, and ROI selection
    for the microfluidics platform. It integrates with the PiStrobeCam
    class to provide synchronized camera-strobe operation.

    Attributes:
        thread: Background thread for frame capture
        frame: Current frame data (JPEG bytes)
        exit_event: Event to signal thread termination
        socketio: Flask-SocketIO instance for WebSocket communication
        strobe_cam: PiStrobeCam instance for camera-strobe integration
        camera: Camera abstraction layer instance
        strobe_data: Dictionary containing strobe state and parameters
        strobe_period_ns: Strobe pulse period in nanoseconds
        enabled: Whether the camera is enabled
        cam_read_time_us: Camera read time in microseconds
        cam_data: Dictionary containing camera state
        roi: ROI coordinates dictionary or None
        optimize_fps_btn_enabled: Whether FPS optimization button is enabled
    """

    def __init__(self, exit_event: threading.Event, socketio: Any) -> None:
        """
        Initialize the Camera controller.

        Args:
            exit_event: Threading event to signal application shutdown
            socketio: Flask-SocketIO instance for WebSocket communication
        """
        logger.info("Initializing Camera controller")
        self.exit_event = exit_event
        self.socketio = socketio
        self.thread: Optional[threading.Thread] = None
        self.frame: Optional[bytes] = None

        # Initialize strobe-camera integration
        logger.debug("Creating PiStrobeCam instance")
        self.strobe_cam = PiStrobeCam(PORT_STROBE, STROBE_REPLY_PAUSE_S)
        # Camera is already initialized with default (rpi) in PiStrobeCam.__init__
        self.camera = self.strobe_cam.camera

        # Initialize strobe data with default values
        self.strobe_data: Dict[str, Any] = {
            "hold": 0,
            "enable": 0,
            "wait_ns": 0,
            "period_ns": STROBE_DEFAULT_PERIOD_NS,
            "framerate": 0,
            "cam_read_time_us": 0,
        }
        self.strobe_period_ns = int(self.strobe_data["period_ns"])
        self.cam_read_time_us = 0
        self.optimize_fps_btn_enabled = False

        # Configure strobe
        try:
            valid = self.strobe_cam.strobe.set_enable(self.strobe_data["enable"])
            self.strobe_cam.strobe.set_hold(self.strobe_data["hold"])
            logger.debug("Setting initial strobe timing")
            self.set_timing()
            self.enabled = valid
        except Exception as e:
            logger.error(f"Error initializing strobe: {e}")
            self.enabled = False

        # Initialize camera data
        self.cam_data: Dict[str, Any] = {"camera": CAMERA_TYPE_RPI, "status": ""}

        # ROI storage: dictionary with keys 'x', 'y', 'width', 'height' or None
        self.roi: Optional[Dict[str, int]] = None

        # Register WebSocket event handlers
        self._register_websocket_handlers()

        logger.info("Camera initialization complete")

    def _register_websocket_handlers(self) -> None:
        """
        Register WebSocket event handlers for camera, strobe, and ROI.

        Only registers handlers if socketio is available.
        """
        if self.socketio is None:
            logger.warning("Cannot register WebSocket handlers: socketio is None")
            return

        @self.socketio.on(WS_EVENT_CAM)
        def on_cam(data: Dict[str, Any]) -> None:
            self.on_cam(data)

        @self.socketio.on(WS_EVENT_STROBE)
        def on_strobe(data: Dict[str, Any]) -> None:
            self.on_strobe(data)

        @self.socketio.on(WS_EVENT_ROI)
        def on_roi(data: Dict[str, Any]) -> None:
            self.on_roi(data)

    def initialize(self) -> None:
        """
        Initialize the camera thread if not already running.

        Starts the background frame capture thread and waits for the first frame
        to be available. If the camera is set to 'none', the thread is not started.
        """
        if self.thread is not None:
            return  # Thread already initialized

        # Don't start camera thread if camera is set to "none"
        if self.cam_data.get("camera") == CAMERA_TYPE_NONE:
            logger.debug("Camera is set to 'none', not initializing thread")
            return

        # Ensure camera is started before starting thread
        if (
            not hasattr(self.camera, "cam_running_event")
            or not self.camera.cam_running_event
            or not self.camera.cam_running_event.is_set()
        ):
            try:
                self.camera.start()
            except Exception as e:
                logger.error(f"Error starting camera: {e}")
                return

        # Start background frame thread
        self.thread = threading.Thread(target=self._thread, name="CameraThread")
        self.thread.daemon = True
        self.thread.start()
        logger.debug("Camera thread started")

        # Wait until frames start to be available (with timeout to avoid infinite hang)
        start_time = time.time()
        while self.frame is None:
            if time.time() - start_time > CAMERA_INIT_TIMEOUT_S:
                logger.warning("Camera frame not available after timeout")
                break
            time.sleep(CAMERA_FRAME_WAIT_SLEEP_S)

    def get_frame(self) -> Optional[bytes]:
        """
        Get the current frame as JPEG bytes.

        Returns:
            Current frame as JPEG bytes, or None if no frame is available
        """
        self.initialize()
        return self.frame

    def save(self) -> None:
        """
        Save the current frame as a snapshot image.

        The image is saved to the snapshot folder with a timestamped filename.
        Creates the snapshot folder if it doesn't exist.
        """
        if self.frame is None:
            logger.warning("No frame available to save")
            return

        try:
            img = Image.open(io.BytesIO(self.frame))
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{SNAPSHOT_FILENAME_PREFIX}{current_time}{SNAPSHOT_FILENAME_SUFFIX}"
            filepath = f"{SNAPSHOT_FOLDER}/{filename}"

            # Create folder if it doesn't exist
            import os

            os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

            img.save(filepath, "JPEG")
            logger.info(f"Snapshot saved: {filepath}")
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")

    def _thread(self) -> None:
        """
        Background thread for continuous frame capture.

        This method runs in a separate thread and continuously captures frames
        from the camera. It handles camera configuration, frame generation,
        and graceful shutdown on exit signal.
        """
        logger.info("Camera thread started")

        # Only start camera if not set to "none"
        if self.cam_data.get("camera") == CAMERA_TYPE_NONE:
            logger.info("Camera disabled (set to 'none'), thread exiting")
            self.thread = None
            return

        try:
            # Camera setup using new abstraction
            self.camera.set_config(
                {
                    "Width": CAMERA_THREAD_WIDTH,
                    "Height": CAMERA_THREAD_HEIGHT,
                    "FrameRate": CAMERA_THREAD_FPS,
                }
            )
            logger.debug("Starting camera...")
            self.camera.start()
            logger.info("Camera started, generating frames...")

            # Use new camera abstraction - generate_frames() returns JPEG bytes
            frame_count = 0
            for frame_data in self.camera.generate_frames():
                # Store frame (frame_data is already JPEG bytes)
                self.frame = frame_data
                frame_count += 1
                if frame_count == 1:
                    logger.info("First frame received!")

                # Check for exit signal
                if self.exit_event.is_set():
                    logger.info("Camera thread exiting (exit event set)")
                    break
        except Exception as e:
            logger.error(f"Error in camera thread: {e}")
        finally:
            try:
                self.camera.close()
            except Exception as e:
                logger.error(f"Error closing camera: {e}")
            self.thread = None
            logger.debug("Camera thread terminated")

    def emit(self) -> None:
        """
        Emit current camera and strobe data to all WebSocket clients.

        Sends the current camera state and strobe parameters to all connected
        clients via WebSocket. Only emits if socketio is available.
        """
        if self.socketio is None:
            return  # Cannot emit without socketio

        try:
            self.socketio.emit(WS_EVENT_CAM, self.cam_data)
            self.socketio.emit(WS_EVENT_STROBE, self.strobe_data)
        except Exception as e:
            logger.error(f"Error emitting camera/strobe data: {e}")

    def set_timing(self) -> bool:
        """
        Set strobe timing parameters.

        Configures the strobe pulse period and timing. The period is clamped
        to the maximum allowed value.

        Returns:
            True if timing was set successfully, False otherwise
        """
        try:
            # Clamp strobe period to maximum allowed value
            self.strobe_period_ns = min(self.strobe_period_ns, STROBE_MAX_PERIOD_NS)
            valid = self.strobe_cam.set_timing(
                STROBE_PRE_PADDING_NS, self.strobe_period_ns, STROBE_POST_PADDING_NS
            )
            self.optimize_fps_btn_enabled = True
            if valid:
                self.enabled = True
            return valid
        except Exception as e:
            logger.error(f"Error setting strobe timing: {e}")
            return False

    def optimize_fps(self) -> None:
        """
        Optimize FPS by iteratively adjusting strobe timing based on camera read time.

        This method performs an iterative optimization loop to find the optimal
        strobe post-padding time based on the actual camera read time. It continues
        until convergence or maximum tries are reached.
        """
        logger.info("Starting FPS optimization")
        cam_read_time_us = 10000  # Initial estimate
        cam_read_time_us_prev = 0
        strobe_post_padding_ns = 1000000  # Start with 1ms
        tries = FPS_OPTIMIZATION_MAX_TRIES

        while (
            abs(cam_read_time_us - cam_read_time_us_prev)
            > FPS_OPTIMIZATION_CONVERGENCE_THRESHOLD_US
        ):
            cam_read_time_us_prev = cam_read_time_us

            try:
                self.strobe_cam.set_timing(
                    STROBE_PRE_PADDING_NS, self.strobe_period_ns, strobe_post_padding_ns
                )
                valid, cam_read_time_us = self.strobe_cam.strobe.get_cam_read_time()

                if not valid:
                    logger.warning("Failed to get camera read time during optimization")
                    break

                # Calculate new post-padding based on actual read time
                strobe_post_padding_ns = (
                    cam_read_time_us + FPS_OPTIMIZATION_POST_PADDING_OFFSET_US
                ) * 1000
                logger.debug(
                    f"FPS optimization: read_time={cam_read_time_us}us, padding={strobe_post_padding_ns}ns"
                )
            except Exception as e:
                logger.error(f"Error during FPS optimization: {e}")
                break

            tries -= 1
            if tries <= 0:
                logger.warning("FPS optimization reached maximum tries")
                break

        logger.info(f"FPS optimization complete: read_time={cam_read_time_us}us")

    def update(self) -> None:
        """
        Update camera read time and framerate from hardware.

        Reads the current camera read time from the strobe controller and
        updates the framerate from the camera configuration.
        """
        try:
            valid, cam_read_time_us = self.strobe_cam.strobe.get_cam_read_time()
            if valid:
                self.cam_read_time_us = cam_read_time_us
        except Exception as e:
            logger.error(f"Error updating camera read time: {e}")

        # Get framerate from camera config (new abstraction)
        try:
            config_value = self.strobe_cam.camera.config.get("FrameRate", CAMERA_THREAD_FPS)
            if isinstance(config_value, (int, float)):
                self.strobe_framerate = int(config_value)
            else:
                self.strobe_framerate = CAMERA_THREAD_FPS
        except (AttributeError, KeyError, ValueError) as e:
            logger.warning(f"Error getting framerate from camera config: {e}")
            self.strobe_framerate = CAMERA_THREAD_FPS

    def update_strobe_data(self) -> None:
        """
        Update strobe data dictionary with current values.

        Refreshes all strobe parameters in the strobe_data dictionary
        for WebSocket transmission.
        """
        self.update()
        self.strobe_data["cam_read_time_us"] = self.cam_read_time_us
        self.strobe_data["period_ns"] = self.strobe_period_ns
        self.strobe_data["framerate"] = self.strobe_framerate

    def on_strobe(self, data: Dict[str, Any]) -> None:
        """
        Handle WebSocket strobe control commands.

        Processes strobe control commands from the web interface:
        - 'hold': Enable/disable strobe hold mode
        - 'enable': Enable/disable strobe
        - 'timing': Set strobe timing parameters

        Args:
            data: Dictionary containing 'cmd' and 'parameters' keys
        """
        try:
            cmd = data.get("cmd")
            params = data.get("parameters", {})

            if cmd == CMD_HOLD:
                hold_on = 1 if params.get("on", 0) != 0 else 0
                valid = self.strobe_cam.strobe.set_hold(hold_on)
                if valid:
                    self.strobe_data["hold"] = hold_on
                    logger.debug(f"Strobe hold set to: {hold_on}")
                else:
                    logger.warning("Failed to set strobe hold")

            elif cmd == CMD_ENABLE:
                enabled = params.get("on", 0) != 0
                valid = self.strobe_cam.strobe.set_enable(enabled)
                if valid:
                    self.strobe_data["enable"] = enabled
                    logger.debug(f"Strobe enabled: {enabled}")
                else:
                    logger.warning("Failed to set strobe enable")

            elif cmd == CMD_TIMING:
                period_ns = int(params.get("period_ns", self.strobe_period_ns))
                self.strobe_period_ns = period_ns
                valid = self.set_timing()
                if not valid:
                    logger.warning("Failed to set strobe timing")
            else:
                logger.warning(f"Unknown strobe command: {cmd}")

            self.update_strobe_data()
            if self.socketio:
                self.socketio.emit(WS_EVENT_STROBE, self.strobe_data)
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error processing strobe command: {e}")
            logger.debug(f"Command data: {data}")

    def on_cam(self, data: Dict[str, Any]) -> None:
        """
        Handle WebSocket camera control commands.

        Processes camera control commands from the web interface:
        - 'snapshot': Save current frame as snapshot
        - 'optimize': Run FPS optimization routine

        Args:
            data: Dictionary containing 'cmd' and optional 'parameters' keys
        """
        try:
            cmd = data.get("cmd")

            if cmd == CMD_SNAPSHOT:
                logger.info("Snapshot requested")
                self.save()
            elif cmd == CMD_OPTIMIZE:
                logger.info("FPS optimization requested")
                self.optimize_fps()
            else:
                logger.warning(f"Unknown camera command: {cmd}")

            self.update_strobe_data()
            if self.socketio:
                self.socketio.emit(WS_EVENT_STROBE, self.strobe_data)
        except Exception as e:
            logger.error(f"Error processing camera command: {e}")
            logger.debug(f"Command data: {data}")

    def on_roi(self, data: Dict[str, Any]) -> None:
        """
        Handle WebSocket ROI (Region of Interest) commands.

        Processes ROI control commands from the web interface:
        - 'set': Set ROI coordinates from client
        - 'get': Get current ROI and send to client
        - 'clear': Clear the current ROI

        Args:
            data: Dictionary containing 'cmd' and optional 'parameters' keys
        """
        try:
            cmd = data.get("cmd")
            if cmd == CMD_SET:
                self._handle_roi_set(data)
            elif cmd == CMD_GET:
                self._handle_roi_get()
            elif cmd == CMD_CLEAR:
                self._handle_roi_clear()
            else:
                logger.warning(f"Unknown ROI command: {cmd}")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error processing ROI command: {e}")
            logger.debug(f"Command data: {data}")

    def _handle_roi_set(self, data: Dict[str, Any]) -> None:
        """Handle ROI set command."""
        params = data.get("parameters", {})
        self.roi = {
            "x": int(params.get("x", 0)),
            "y": int(params.get("y", 0)),
            "width": int(params.get("width", 0)),
            "height": int(params.get("height", 0)),
        }
        logger.info(
            f"ROI set: ({self.roi['x']}, {self.roi['y']}) "
            f"{self.roi['width']}×{self.roi['height']}"
        )
        if self.socketio:
            self.socketio.emit(WS_EVENT_ROI, {"roi": self.roi})

    def _handle_roi_get(self) -> None:
        """Handle ROI get command."""
        if self.socketio:
            roi_data = self.roi if self.roi else None
            self.socketio.emit(WS_EVENT_ROI, {"roi": roi_data})

    def _handle_roi_clear(self) -> None:
        """Handle ROI clear command."""
        if self.roi is not None:
            logger.info("ROI cleared")
        self.roi = None
        if self.socketio:
            self.socketio.emit(WS_EVENT_ROI, {"roi": None})

    def get_roi(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get current ROI coordinates as a tuple.

        Returns:
            Tuple of (x, y, width, height) in image coordinates, or None if not set
        """
        if self.roi:
            return (self.roi["x"], self.roi["y"], self.roi["width"], self.roi["height"])
        return None
