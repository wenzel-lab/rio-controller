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
        CAMERA_TYPE_RPI_HQ,
        SNAPSHOT_FOLDER,
        SNAPSHOT_FILENAME_PREFIX,
        SNAPSHOT_FILENAME_SUFFIX,
        SNAPSHOT_RESOLUTION_DISPLAY,
        SNAPSHOT_RESOLUTION_FULL,
        SNAPSHOT_RESOLUTION_CUSTOM,
        FPS_OPTIMIZATION_MAX_TRIES,
        FPS_OPTIMIZATION_CONVERGENCE_THRESHOLD_US,
        FPS_OPTIMIZATION_POST_PADDING_OFFSET_US,
        CAMERA_SNAPSHOT_JPEG_QUALITY,
        WS_EVENT_CAM,
        WS_EVENT_STROBE,
        WS_EVENT_ROI,
        CMD_SNAPSHOT,
        CMD_OPTIMIZE,
        CMD_SET_RESOLUTION,
        CMD_SET_SNAPSHOT_RESOLUTION,
        CMD_HOLD,
        CMD_ENABLE,
        CMD_TIMING,
        CMD_SET,
        CMD_GET,
        CMD_CLEAR,
        CAMERA_RESOLUTION_PRESETS,
        CAMERA_V2_MAX_WIDTH,
        CAMERA_V2_MAX_HEIGHT,
        CAMERA_HQ_MAX_WIDTH,
        CAMERA_HQ_MAX_HEIGHT,
        SNAPSHOT_RESOLUTION_DISPLAY,
        SNAPSHOT_RESOLUTION_FULL,
        SNAPSHOT_RESOLUTION_CUSTOM,
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

    def __init__(
        self, exit_event: threading.Event, socketio: Any, droplet_controller: Optional[Any] = None
    ) -> None:
        """
        Initialize the Camera controller.

        Args:
            exit_event: Threading event to signal application shutdown
            socketio: Flask-SocketIO instance for WebSocket communication
            droplet_controller: Optional DropletDetectorController instance for frame feeding
        """
        logger.debug("Initializing Camera controller")
        self.exit_event = exit_event
        self.socketio = socketio
        self.thread: Optional[threading.Thread] = None
        self.frame: Optional[bytes] = None
        self.droplet_controller = droplet_controller  # Optional droplet detector controller

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

        # Resolution settings
        self.display_resolution: Tuple[int, int] = (CAMERA_THREAD_WIDTH, CAMERA_THREAD_HEIGHT)
        self.snapshot_resolution_mode: str = (
            SNAPSHOT_RESOLUTION_DISPLAY  # "display", "full", or "custom"
        )
        self.snapshot_resolution: Optional[Tuple[int, int]] = None  # Used if mode is "custom"

        # Display FPS (separate from capture FPS to reduce Pi load)
        from config import CAMERA_DISPLAY_FPS

        self.display_fps: float = float(CAMERA_DISPLAY_FPS)

        # Initialize cam_data with resolution info
        self.cam_data["display_width"] = self.display_resolution[0]
        self.cam_data["display_height"] = self.display_resolution[1]
        self.cam_data["snapshot_resolution_mode"] = self.snapshot_resolution_mode
        self.cam_data["display_fps"] = self.display_fps

        # Camera calibration for droplet detection
        # um_per_px: micrometers per pixel (calibration factor)
        # radius_offset_px: pixel offset to correct for threshold bias
        self.calibration: Dict[str, float] = {
            "um_per_px": 1.0,  # Default: 1 um per pixel (no calibration)
            "radius_offset_px": 0.0,  # Default: no offset correction
        }

        # Register WebSocket event handlers
        self._register_websocket_handlers()

        logger.debug("Camera initialization complete")

    def _get_snapshot_resolution(self) -> Tuple[int, int]:
        """
        Get the resolution to use for snapshots based on current settings.

        Returns:
            Tuple[int, int]: (width, height) for snapshot
        """
        if self.snapshot_resolution_mode == SNAPSHOT_RESOLUTION_DISPLAY:
            return self.display_resolution
        elif self.snapshot_resolution_mode == SNAPSHOT_RESOLUTION_FULL:
            # Determine max resolution based on camera type
            camera_type = self.cam_data.get("camera", CAMERA_TYPE_RPI)
            if camera_type == CAMERA_TYPE_RPI_HQ:
                return (CAMERA_HQ_MAX_WIDTH, CAMERA_HQ_MAX_HEIGHT)
            else:
                return (CAMERA_V2_MAX_WIDTH, CAMERA_V2_MAX_HEIGHT)
        elif self.snapshot_resolution_mode == SNAPSHOT_RESOLUTION_CUSTOM:
            if self.snapshot_resolution:
                return self.snapshot_resolution
            else:
                return self.display_resolution
        else:
            return self.display_resolution

    def _handle_set_resolution(self, params: Dict[str, Any]) -> None:
        """
        Handle set_resolution command.

        Args:
            params: Dictionary with 'preset' (str) or 'width' and 'height' (int)
        """
        try:
            # Determine new resolution
            new_resolution = None
            if "preset" in params:
                preset_name = params["preset"]
                if preset_name in CAMERA_RESOLUTION_PRESETS:
                    new_resolution = CAMERA_RESOLUTION_PRESETS[preset_name]
                else:
                    logger.warning(f"Unknown resolution preset: {preset_name}")
                    return
            elif "width" in params and "height" in params:
                width = int(params["width"])
                height = int(params["height"])
                # Validate resolution values (basic sanity check)
                if width <= 0 or height <= 0 or width > 5000 or height > 5000:
                    logger.warning(f"Invalid resolution values: {width}x{height}")
                    return
                new_resolution = (width, height)
            else:
                logger.warning("set_resolution requires 'preset' or 'width' and 'height'")
                return

            # Validate against camera limits (if camera is available)
            if self.camera is not None and new_resolution:
                camera_type = self.cam_data.get("camera", CAMERA_TYPE_RPI)
                max_width = (
                    CAMERA_HQ_MAX_WIDTH
                    if camera_type == CAMERA_TYPE_RPI_HQ
                    else CAMERA_V2_MAX_WIDTH
                )
                max_height = (
                    CAMERA_HQ_MAX_HEIGHT
                    if camera_type == CAMERA_TYPE_RPI_HQ
                    else CAMERA_V2_MAX_HEIGHT
                )

                if new_resolution[0] > max_width or new_resolution[1] > max_height:
                    logger.warning(
                        f"Resolution {new_resolution[0]}x{new_resolution[1]} exceeds camera maximum "
                        f"({max_width}x{max_height}), clamping to maximum"
                    )
                    new_resolution = (
                        min(new_resolution[0], max_width),
                        min(new_resolution[1], max_height),
                    )

            self.display_resolution = new_resolution
            logger.info(
                f"Setting display resolution to {self.display_resolution[0]}x{self.display_resolution[1]}"
            )

            # Update cam_data (so UI can show the change immediately)
            self.cam_data["display_width"] = self.display_resolution[0]
            self.cam_data["display_height"] = self.display_resolution[1]

            # Emit update immediately so UI reflects the change
            if self.socketio:
                self.socketio.emit(WS_EVENT_CAM, self.cam_data)

            # Update camera configuration if camera is available
            if self.camera is not None:
                try:
                    self.camera.set_config(
                        {
                            "Width": self.display_resolution[0],
                            "Height": self.display_resolution[1],
                        }
                    )

                    # Restart camera thread to apply new resolution
                    self._restart_camera_thread()
                except Exception as e:
                    logger.error(f"Error applying resolution change: {e}")
            else:
                logger.warning(
                    "Camera not available, resolution setting will apply when camera starts"
                )

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error setting resolution: {e}")
            logger.debug(f"Parameters: {params}")

    def _handle_set_snapshot_resolution(self, params: Dict[str, Any]) -> None:
        """
        Handle set_snapshot_resolution command.

        Args:
            params: Dictionary with 'mode' (str: "display", "full", "custom")
                    and optionally 'width' and 'height' (int) for custom mode
        """
        try:
            mode = params.get("mode", SNAPSHOT_RESOLUTION_DISPLAY)
            if mode not in (
                SNAPSHOT_RESOLUTION_DISPLAY,
                SNAPSHOT_RESOLUTION_FULL,
                SNAPSHOT_RESOLUTION_CUSTOM,
            ):
                logger.warning(f"Unknown snapshot resolution mode: {mode}")
                return

            self.snapshot_resolution_mode = mode

            if mode == SNAPSHOT_RESOLUTION_CUSTOM:
                if "width" in params and "height" in params:
                    self.snapshot_resolution = (int(params["width"]), int(params["height"]))
                else:
                    logger.warning("Custom snapshot resolution requires 'width' and 'height'")
                    self.snapshot_resolution_mode = SNAPSHOT_RESOLUTION_DISPLAY

            logger.debug(f"Snapshot resolution mode set to: {mode}")
            if self.snapshot_resolution:
                logger.info(
                    f"Custom snapshot resolution: {self.snapshot_resolution[0]}x{self.snapshot_resolution[1]}"
                )

            # Update cam_data
            self.cam_data["snapshot_resolution_mode"] = self.snapshot_resolution_mode
            if self.snapshot_resolution:
                self.cam_data["snapshot_width"] = self.snapshot_resolution[0]
                self.cam_data["snapshot_height"] = self.snapshot_resolution[1]
            else:
                # Clear custom snapshot resolution if not set
                self.cam_data.pop("snapshot_width", None)
                self.cam_data.pop("snapshot_height", None)

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error setting snapshot resolution: {e}")
            logger.debug(f"Parameters: {params}")

    def _restart_camera_thread(self) -> None:
        """
        Restart the camera thread to apply new resolution settings.

        This method safely stops the current camera thread, clears the exit event,
        and restarts the camera with new settings. Uses proper synchronization
        to avoid race conditions.
        """
        try:
            # Stop current thread if running
            if self.thread is not None and self.thread.is_alive():
                logger.debug("Stopping camera thread for resolution change")

                # Set exit event to signal camera thread loop to exit
                # Note: exit_event is shared with app shutdown, but we'll clear it after thread stops
                if hasattr(self, "exit_event"):
                    self.exit_event.set()

                # Wait for thread to finish (with timeout)
                try:
                    self.thread.join(timeout=2.0)
                    if self.thread.is_alive():
                        logger.warning("Camera thread did not stop within timeout")
                except Exception as e:
                    logger.warning(f"Error waiting for thread to stop: {e}")

                # Clear thread reference
                self.thread = None

            # Clear exit event before restarting (important for resolution changes)
            # Note: This is safe because if the app is shutting down, close() will set exit_event again
            if hasattr(self, "exit_event"):
                self.exit_event.clear()

            # Stop camera hardware to allow reconfiguration
            if self.camera is not None and hasattr(self.camera, "stop"):
                try:
                    self.camera.stop()
                except Exception as e:
                    logger.warning(f"Error stopping camera hardware: {e}")

            # Restart camera if needed
            if self.camera and self.cam_data.get("camera") != CAMERA_TYPE_NONE:
                try:
                    # Camera will be reconfigured when thread restarts with new resolution
                    # Initialize thread again
                    self.initialize()
                except Exception as e:
                    logger.error(f"Error restarting camera thread: {e}")
        except Exception as e:
            logger.error(f"Error in _restart_camera_thread: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    def _register_websocket_handlers(self) -> None:
        """
        Register WebSocket event handlers for camera, strobe, and ROI.

        Only registers handlers if socketio is available.
        """
        if self.socketio is None:
            logger.warning("Cannot register WebSocket handlers: socketio is None")
            return

        logger.debug(f"Registering WebSocket handlers: {WS_EVENT_CAM}, {WS_EVENT_STROBE}, {WS_EVENT_ROI}")

        @self.socketio.on(WS_EVENT_CAM)
        def on_cam(data: Dict[str, Any]) -> None:
            self.on_cam(data)

        @self.socketio.on(WS_EVENT_STROBE)
        def on_strobe(data: Dict[str, Any]) -> None:
            logger.debug(f"WebSocket handler received strobe event: {data}")
            self.on_strobe(data)

        @self.socketio.on(WS_EVENT_ROI)
        def on_roi(data: Dict[str, Any]) -> None:
            self.on_roi(data)

        logger.debug("WebSocket handlers registered successfully")

    def initialize(self) -> None:
        """
        Initialize the camera thread if not already running.

        Starts the background frame capture thread and waits for the first frame
        to be available. If the camera is set to 'none', the thread is not started.
        """
        if self.thread is not None and self.thread.is_alive():
            logger.debug("Camera thread already running, skipping initialization")
            return  # Thread already running

        # Don't start camera thread if camera is set to "none"
        if self.cam_data.get("camera") == CAMERA_TYPE_NONE:
            logger.debug("Camera is set to 'none', not initializing thread")
            return

        # Ensure camera is started before starting thread
        if self.camera is None:
            logger.error("Camera is None, cannot start thread")
            return
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
        # Don't try to initialize if camera is None (prevents error spam)
        if self.camera is None:
            return None
        
        # Only initialize if camera thread is not running to avoid repeated starts
        if self.thread is None or not self.thread.is_alive():
            self.initialize()
        return self.frame

    def save(self) -> None:
        """
        Save the current frame as a snapshot image.

        The image is saved to the snapshot folder with a timestamped filename.
        Creates the snapshot folder if it doesn't exist.

        If snapshot resolution mode is "full" or "custom", captures at that resolution.
        Otherwise, uses the current display frame.
        """
        try:
            import os

            os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

            # Determine snapshot resolution
            snapshot_width, snapshot_height = self._get_snapshot_resolution()

            # Determine if we can use current frame or need to capture at resolution
            use_current_frame = (
                snapshot_width == self.display_resolution[0]
                and snapshot_height == self.display_resolution[1]
                and self.frame is not None
            )

            img = None
            frame_data = None

            if use_current_frame:
                # Use current frame (fast path - no camera capture needed)
                frame_data = self.frame
            else:
                # Need to capture at snapshot resolution
                if self.camera is None:
                    logger.warning("Camera not available for snapshot")
                    if self.frame is None:
                        logger.error(
                            "No frame available and camera not available - cannot save snapshot"
                        )
                        return
                    # Fallback to current frame even if resolution doesn't match
                    logger.info(
                        f"Using current frame for snapshot (requested {snapshot_width}x{snapshot_height})"
                    )
                    frame_data = self.frame
                else:
                    try:
                        logger.debug(f"Capturing snapshot at {snapshot_width}x{snapshot_height}")
                        frame_data = self.camera.capture_frame_at_resolution(
                            snapshot_width, snapshot_height
                        )
                    except Exception as e:
                        logger.error(f"Error capturing at {snapshot_width}x{snapshot_height}: {e}")
                        # Fallback to current frame if available
                        if self.frame is not None:
                            logger.info("Falling back to current frame")
                            frame_data = self.frame
                        else:
                            logger.error(
                                "No frame available and capture failed - cannot save snapshot"
                            )
                            return

            # Convert frame data to PIL Image (single conversion)
            if frame_data is None:
                logger.error("No image data available for snapshot")
                return

            try:
                img = Image.open(io.BytesIO(frame_data))
            except Exception as e:
                logger.error(f"Error reading image data: {e}")
                return

            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{SNAPSHOT_FILENAME_PREFIX}{current_time}{SNAPSHOT_FILENAME_SUFFIX}"
            filepath = f"{SNAPSHOT_FOLDER}/{filename}"

            img.save(filepath, "JPEG", quality=CAMERA_SNAPSHOT_JPEG_QUALITY)
            logger.info(
                f"Snapshot saved: {filepath} ({snapshot_width}x{snapshot_height}, size: {img.size[0]}x{img.size[1]})"
            )
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    def _feed_frame_to_droplet_detector(self) -> None:
        """
        Feed current frame to droplet detector if conditions are met.

        This method safely extracts ROI frame and feeds it to the droplet
        detector without breaking the camera thread on errors.
        Only feeds frames when detection is actively running (needed for data collection).
        """
        # Conditional processing: only feed frames when detection is actively running
        # This prevents unnecessary processing when detection is stopped, but ensures
        # all frames are processed when running (no frame skipping - we need the data)
        if (
            self.droplet_controller is None
            or self.roi is None
            or not self.droplet_controller.running
        ):
            return

        try:
            # Get ROI frame as numpy array for droplet detection
            # Note: We need to get the raw frame array, not JPEG bytes
            # The camera abstraction provides get_frame_roi() method
            if not (self.strobe_cam and self.strobe_cam.camera):
                return

            roi = (
                self.roi["x"],
                self.roi["y"],
                self.roi["width"],
                self.roi["height"],
            )
            roi_frame = self.strobe_cam.get_frame_roi(roi)
            if roi_frame is not None:
                # Add frame to droplet detector processing queue
                self.droplet_controller.add_frame(roi_frame)
        except Exception as e:
            # Don't break camera thread if droplet detection fails
            logger.debug(f"Error feeding frame to droplet detector: {e}")

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

        if self.camera is None:
            # Log once (not repeatedly) and exit thread gracefully
            logger.error("Camera is None, camera thread exiting (check camera hardware connection)")
            self.thread = None
            return

        try:
            # Camera setup using new abstraction
            # Set display resolution
            self.camera.set_config(
                {
                    "Width": self.display_resolution[0],
                    "Height": self.display_resolution[1],
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
                    logger.debug("First frame received")

                # Feed frame to droplet detector if available and ROI is set
                self._feed_frame_to_droplet_detector()

                # Check for exit signal
                if self.exit_event.is_set():
                    logger.info("Camera thread exiting (exit event set)")
                    break
        except Exception as e:
            logger.error(f"Error in camera thread: {e}")
        finally:
            if self.camera is not None:
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
        
        Note: In strobe-centric mode, get_cam_read_time() may not work reliably
        if the strobe is not enabled. The optimization will fail gracefully if
        camera read time cannot be obtained.
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
                
                # Get camera read time with timeout protection (SPI call may hang)
                valid, cam_read_time_us = self.strobe_cam.strobe.get_cam_read_time()

                if not valid:
                    logger.warning("Failed to get camera read time during optimization - strobe may need to be enabled")
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
                import traceback
                logger.debug(traceback.format_exc())
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
            if self.strobe_cam.camera is None:
                self.strobe_framerate = CAMERA_THREAD_FPS
                return
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
        logger.debug(f"on_strobe() called with data: {data}")
        try:
            cmd = data.get("cmd")
            params = data.get("parameters", {})

            if cmd == CMD_HOLD:
                hold_on = 1 if params.get("on", 0) != 0 else 0
                valid = self.strobe_cam.strobe.set_hold(hold_on)
                # Always update strobe_data to match user intent (matches old implementation)
                self.strobe_data["hold"] = hold_on
                if valid:
                    logger.info(f"Strobe hold set to: {hold_on}")
                else:
                    logger.warning(
                        f"Failed to set strobe hold to {hold_on} - check hardware connection"
                    )

            elif cmd == CMD_ENABLE:
                enabled = params.get("on", 0) != 0
                valid = self.strobe_cam.strobe.set_enable(enabled)
                # Always update strobe_data to match user intent (matches old implementation)
                # This ensures UI reflects what user tried to set, even if hardware call failed
                self.strobe_data["enable"] = enabled
                if valid:
                    logger.info(f"Strobe {'ENABLED' if enabled else 'DISABLED'} successfully")
                else:
                    logger.error(
                        f"⚠️ CRITICAL: Failed to set strobe enable to {enabled} - hardware may not be responding! Check SPI connection and strobe hardware power."
                    )

            elif cmd == CMD_TIMING:
                period_ns = int(params.get("period_ns", self.strobe_period_ns))
                wait_ns = int(params.get("wait_ns", STROBE_PRE_PADDING_NS))
                self.strobe_period_ns = period_ns
                # Set timing with both wait and period
                # Note: Don't automatically enable strobe here - let user control it explicitly
                valid = self.strobe_cam.set_timing(wait_ns, period_ns, STROBE_POST_PADDING_NS)
                if not valid:
                    logger.warning("Failed to set strobe timing")
                else:
                    logger.debug(f"Strobe timing set: period={period_ns}ns, wait={wait_ns}ns")
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
        - 'set_resolution': Set display/streaming resolution
        - 'set_snapshot_resolution': Set snapshot resolution mode

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
            elif cmd == CMD_SET_RESOLUTION:
                self._handle_set_resolution(data.get("parameters", {}))
            elif cmd == CMD_SET_SNAPSHOT_RESOLUTION:
                self._handle_set_snapshot_resolution(data.get("parameters", {}))
            else:
                logger.warning(f"Unknown camera command: {cmd}")

            self.update_strobe_data()
            if self.socketio:
                self.socketio.emit(WS_EVENT_STROBE, self.strobe_data)
                self.socketio.emit(WS_EVENT_CAM, self.cam_data)
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
        """Handle ROI set command with validation and hardware ROI for Mako."""
        params = data.get("parameters", {})
        roi_tuple = (
            int(params.get("x", 0)),
            int(params.get("y", 0)),
            int(params.get("width", 0)),
            int(params.get("height", 0)),
        )

        # Validate and snap ROI if camera supports constraint validation
        if self.camera and hasattr(self.camera, "validate_and_snap_roi"):
            try:
                roi_tuple = self.camera.validate_and_snap_roi(roi_tuple)
                logger.debug("ROI validated and snapped to camera constraints")
            except Exception as e:
                logger.warning(f"ROI validation failed, using raw values: {e}")

        self.roi = {
            "x": roi_tuple[0],
            "y": roi_tuple[1],
            "width": roi_tuple[2],
            "height": roi_tuple[3],
        }

        # Software ROI only - hardware ROI requires camera restart which causes issues
        # Using software cropping for now - works reliably without camera restart
        logger.debug(f"ROI set (software cropping): {roi_tuple}")

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

            # Include camera constraints if available (for Mako cameras)
            constraints = None
            if self.camera and hasattr(self.camera, "get_roi_constraints"):
                try:
                    constraints = self.camera.get_roi_constraints()
                except Exception as e:
                    logger.debug(f"Could not get ROI constraints: {e}")

            response = {"roi": roi_data}
            if constraints:
                response["constraints"] = constraints

            self.socketio.emit(WS_EVENT_ROI, response)

    def _handle_roi_clear(self) -> None:
        """Handle ROI clear command. Software ROI only (hardware ROI disabled for stability)."""
        if self.roi is not None:
            logger.info("ROI cleared")

        self.roi = None
        if self.socketio:
            self.socketio.emit(WS_EVENT_ROI, {"roi": None})

    def get_calibration(self) -> Dict[str, float]:
        """
        Get camera calibration parameters for droplet detection.

        Returns:
            Dictionary with 'um_per_px' and 'radius_offset_px' keys
        """
        return self.calibration.copy()

    def set_calibration(
        self, um_per_px: Optional[float] = None, radius_offset_px: Optional[float] = None
    ) -> None:
        """
        Set camera calibration parameters for droplet detection.

        Args:
            um_per_px: Micrometers per pixel (calibration factor)
            radius_offset_px: Pixel offset to correct for threshold bias
        """
        if um_per_px is not None:
            self.calibration["um_per_px"] = float(um_per_px)
            logger.info(f"Camera calibration updated: um_per_px = {um_per_px}")
        if radius_offset_px is not None:
            self.calibration["radius_offset_px"] = float(radius_offset_px)
            logger.info(f"Camera calibration updated: radius_offset_px = {radius_offset_px}")

    def get_roi(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get current ROI coordinates as a tuple.

        Returns:
            Tuple of (x, y, width, height) in image coordinates, or None if not set
        """
        if self.roi:
            return (self.roi["x"], self.roi["y"], self.roi["width"], self.roi["height"])
        return None

    def close(self) -> None:
        """
        Close camera and clean up resources.

        Properly shuts down the camera thread, camera, and strobe,
        ensuring all resources are released.
        """
        try:
            # Signal thread to exit
            if self.exit_event:
                self.exit_event.set()

            # Wait for thread to finish
            if self.thread is not None and self.thread.is_alive():
                self.thread.join(timeout=5.0)

            # Close strobe-camera integration
            if hasattr(self, "strobe_cam") and self.strobe_cam:
                self.strobe_cam.close()

            logger.info("Camera controller closed")
        except Exception as e:
            logger.error(f"Error closing camera controller: {e}")
