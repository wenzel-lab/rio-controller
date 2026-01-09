"""
PiCamera Legacy Implementation (32-bit)
Based on tested PiCamera32 code from flow-microscopy-platform

Uses picamera library for 32-bit Raspberry Pi OS
"""

from picamera import PiCamera
import io
import time
import threading
from typing import Optional, Dict, Tuple, Generator, Any
import numpy as np
from queue import Queue
from threading import Event
import logging

from .camera_base import BaseCamera

# Import JPEG quality configuration
try:
    from config import CAMERA_STREAMING_JPEG_QUALITY, CAMERA_SNAPSHOT_JPEG_QUALITY
except ImportError:
    # Fallback if config not available
    CAMERA_STREAMING_JPEG_QUALITY = 75
    CAMERA_SNAPSHOT_JPEG_QUALITY = 95

logger = logging.getLogger(__name__)


class PiCameraLegacy(BaseCamera):
    """
    Raspberry Pi Camera implementation for 32-bit OS

    Uses picamera library (legacy, but stable on 32-bit)
    Based on tested code from flow-microscopy-platform/module-user_interface/webapp/plugins/devices/pi_camera_32/core.py
    """

    def __init__(self):
        super().__init__()

        # Initialize threading components (from tested code)
        self.cam_running_event: Event = Event()
        self.capture_flag: Event = Event()
        self.capture_queue: Queue[bytes] = Queue(1)

        # Store last decoded frame for ROI access (updated during generate_frames)
        self._last_frame_array: Optional[np.ndarray] = None
        self._last_frame_lock = threading.Lock()

        # Initialize camera (from tested code pattern)
        # Initialize camera - removed WERKZEUG_RUN_MAIN check as it prevents initialization
        # when running python main.py directly (not through Werkzeug reloader)
        self.cam: Optional[PiCamera] = None
        try:
            self.cam = PiCamera()
        except Exception as e:
            logger.error(f"Failed to initialize PiCamera: {e}")
            self.cam = None

        # Default configuration (from tested code)
        self.config: Dict[str, Any] = {
            "size": [640, 480],
            "ExposureTime": 10000,
            "FrameRate": 30,
            "ShutterSpeed": 10000,
        }
        self.frame_rate = 30

        # Store original crop for ROI support
        self._original_crop = None

        # Hardware ROI state (for persistent hardware ROI)
        self.hardware_roi = None  # (x, y, width, height) in sensor coordinates

    def start(self) -> None:
        """Start camera (picamera is always running, but ensure it's configured)"""
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        # Configure camera with current settings
        size_config = self.config.get("size", [640, 480])
        if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
            self.cam.resolution = (int(size_config[0]), int(size_config[1]))
        else:
            self.cam.resolution = (640, 480)
        framerate = self.config.get("FrameRate", 30)
        if isinstance(framerate, (int, float)):
            self.cam.framerate = int(framerate)
        shutter = self.config.get("ShutterSpeed", 10000)
        if isinstance(shutter, (int, float)):
            self.cam.shutter_speed = int(shutter)
        self.cam.awb_mode = "auto"
        self.cam.exposure_mode = "off"
        # Note: JPEG quality is set in capture_continuous() call, not as camera attribute

    def stop(self) -> None:
        """Stop camera recording"""
        if self.cam and self.cam.recording:
            self.cam.stop_recording()
        self.cam_running_event.clear()

    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        """
        Generate frames (generator) - for streaming

        Based on tested implementation from flow-microscopy-platform
        Returns JPEG-encoded frames for web streaming
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        self.cam_running_event.set()
        framerate = self.config.get("FrameRate", 30)
        if isinstance(framerate, (int, float)):
            frame_interval = 1.0 / float(framerate)
        else:
            frame_interval = 1.0 / 30.0

        # Use capture_continuous properly - create stream once and reuse
        # This is more efficient than creating new streams in a loop
        # Set JPEG quality for streaming (lower quality reduces bandwidth/CPU)
        stream = io.BytesIO()
        for frame in self.cam.capture_continuous(
            stream, format="jpeg", use_video_port=True, quality=CAMERA_STREAMING_JPEG_QUALITY
        ):
            if not self.cam_running_event.is_set():
                break

            start_time = time.time()

            # Call frame callback if set (for strobe trigger)
            if self.frame_callback:
                self.frame_callback()

            # Get frame data from stream (JPEG bytes for streaming)
            stream.seek(0)
            data = stream.getvalue()
            stream.seek(0)
            stream.truncate()

            # Decode JPEG frame for ROI access (needed for droplet detection)
            # If hardware ROI is active, the frame is already at ROI resolution (crop applied at sensor)
            # This allows get_frame_roi() to work even while capture_continuous is running
            try:
                from PIL import Image
                import io as io_module

                img = Image.open(io_module.BytesIO(data))
                frame_array = np.array(img.convert("RGB"))
                with self._last_frame_lock:
                    self._last_frame_array = frame_array
            except Exception as e:
                logger.debug(f"Could not decode frame for ROI access: {e}")

            # Return bytes directly (not numpy array) for web streaming
            buffer = data

            # Handle capture request
            if self.capture_flag.is_set():
                self.capture_queue.put(buffer)
                self.capture_flag.clear()

            yield buffer

            # Ensure frame rate is respected (from tested code)
            # But don't sleep if we're already behind (would cause lag)
            elapsed_time = time.time() - start_time
            sleep_time = frame_interval - elapsed_time
            if sleep_time > 0.001:  # Only sleep if we have meaningful time left
                time.sleep(sleep_time)

        self.stop()

    def get_frame_array(self) -> np.ndarray:
        """
        Get single frame as numpy array

        Returns:
            numpy.ndarray: Frame as RGB numpy array
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        # Use capture_array() for numpy output
        frame = self.cam.capture_array()
        # picamera returns RGB, so no conversion needed
        return frame

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI frame. When hardware ROI is set and matches the requested ROI,
        the camera is already capturing at ROI resolution, so we return the full frame.
        Otherwise, we use software cropping from the decoded frame.

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            numpy.ndarray: ROI frame as RGB numpy array

        Note: If hardware ROI is active and matches the requested ROI, the full frame
        is already the ROI region (no cropping needed). Otherwise, software cropping
        is applied to the last decoded frame from the streaming loop.
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        x, y, width, height = roi

        # Check if capture_continuous is running (cam_running_event is set)
        is_capturing = self.cam_running_event.is_set() if self.cam_running_event else False

        try:
            # Software ROI cropping only (hardware ROI disabled for stability)
            if is_capturing:
                # Hardware ROI not matching - use software cropping from decoded frame
                with self._last_frame_lock:
                    if self._last_frame_array is None:
                        logger.warning("No decoded frame available for ROI, returning black frame")
                        return np.zeros((height, width, 3), dtype=np.uint8)
                    frame = self._last_frame_array.copy()

                # Apply software cropping to ROI region
                frame_height, frame_width = frame.shape[:2]

                # Check bounds
                if x + width > frame_width or y + height > frame_height:
                    logger.warning(
                        f"ROI bounds ({x}, {y}, {width}, {height}) exceed frame size ({frame_width}, {frame_height})"
                    )
                    # Clamp to frame bounds
                    x = max(0, min(x, frame_width - 1))
                    y = max(0, min(y, frame_height - 1))
                    width = min(width, frame_width - x)
                    height = min(height, frame_height - y)

                roi_frame = frame[y : y + height, x : x + width]
                return roi_frame
            else:
                # Not capturing continuously - use software cropping on captured frame
                frame = self.cam.capture_array()
                frame_height, frame_width = frame.shape[:2]

                # Check bounds
                if x + width > frame_width or y + height > frame_height:
                    logger.warning(
                        f"ROI bounds ({x}, {y}, {width}, {height}) exceed frame size ({frame_width}, {frame_height})"
                    )
                    # Clamp to frame bounds
                    x = max(0, min(x, frame_width - 1))
                    y = max(0, min(y, frame_height - 1))
                    width = min(width, frame_width - x)
                    height = min(height, frame_height - y)

                roi_frame = frame[y : y + height, x : x + width]
                return roi_frame

        except Exception as e:
            logger.error(f"Error in get_frame_roi: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            # Fallback: return a black frame of correct size
            return np.zeros((height, width, 3), dtype=np.uint8)

    def set_roi_hardware(self, roi: Tuple[int, int, int, int]) -> bool:
        """
        Set hardware ROI on Pi camera using picamera's crop property.

        Args:
            roi: (x, y, width, height) tuple in pixels

        Returns:
            bool: True if hardware ROI was set successfully, False otherwise

        Note:
            This uses picamera's crop property to set sensor-level ROI.
            The camera will only capture the specified region.
            To reset to full frame, set ROI to (0, 0, sensor_width, sensor_height).
        """
        if self.cam is None:
            return False

        x, y, width, height = roi

        try:
            # Get current resolution for normalization
            current_res = self.cam.resolution
            sensor_width, sensor_height = current_res

            # Convert pixel coordinates to normalized coordinates (0.0-1.0)
            norm_x = x / sensor_width
            norm_y = y / sensor_height
            norm_w = width / sensor_width
            norm_h = height / sensor_height

            # Clamp to valid range
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))
            norm_w = max(0.0, min(1.0 - norm_x, norm_w))
            norm_h = max(0.0, min(1.0 - norm_y, norm_h))

            # Set crop (picamera expects (x, y, width, height) in normalized coords)
            self.cam.crop = (norm_x, norm_y, norm_w, norm_h)

            # Store hardware ROI state
            self.hardware_roi = (x, y, width, height)
            logger.info(
                f"Hardware ROI set on Pi camera (legacy): {roi} (normalized: {norm_x:.3f}, {norm_y:.3f}, {norm_w:.3f}, {norm_h:.3f})"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to set hardware ROI on Pi camera (legacy): {e}")
            self.hardware_roi = None
            return False

    def get_max_resolution(self) -> Tuple[int, int]:
        """
        Get maximum sensor resolution for Pi camera

        Returns:
            Tuple[int, int]: (max_width, max_height)
        """
        if self.cam is None:
            return (3280, 2464)  # V2 Camera default

        try:
            # Get current resolution (picamera uses current resolution)
            current_res = self.cam.resolution
            return current_res
        except Exception:
            return (3280, 2464)  # Default fallback

    def get_roi_constraints(self) -> Dict[str, Any]:
        """
        Get ROI constraints for Pi camera (min, max, increment values)

        Returns:
            Dict with keys: offset_x, offset_y, width, height
            Each contains: min, max, increment, current
        """
        max_width, max_height = self.get_max_resolution()

        # Pi cameras typically support arbitrary ROI with 1-pixel increments
        constraints = {
            "offset_x": {"min": 0, "max": max_width, "increment": 1, "current": 0},
            "offset_y": {"min": 0, "max": max_height, "increment": 1, "current": 0},
            "width": {"min": 10, "max": max_width, "increment": 1, "current": max_width},
            "height": {"min": 10, "max": max_height, "increment": 1, "current": max_height},
        }

        # Update current values if hardware ROI is set
        if hasattr(self, "hardware_roi") and self.hardware_roi:
            x, y, w, h = self.hardware_roi
            constraints["offset_x"]["current"] = x
            constraints["offset_y"]["current"] = y
            constraints["width"]["current"] = w
            constraints["height"]["current"] = h

        return constraints

    def validate_and_snap_roi(self, roi: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """
        Validate ROI against camera constraints and snap to valid increments

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            Tuple[int, int, int, int]: Validated and snapped ROI
        """
        x, y, width, height = roi
        constraints = self.get_roi_constraints()

        # Snap to increments (typically 1 pixel for Pi cameras)
        def snap_to_increment(value: int, min_val: int, max_val: int, increment: int) -> int:
            """Snap value to nearest valid increment within range."""
            snapped = round(value / increment) * increment
            return max(min_val, min(max_val, snapped))

        # Snap X and Y
        x = snap_to_increment(
            x,
            constraints["offset_x"]["min"],
            constraints["offset_x"]["max"],
            constraints["offset_x"]["increment"],
        )
        y = snap_to_increment(
            y,
            constraints["offset_y"]["min"],
            constraints["offset_y"]["max"],
            constraints["offset_y"]["increment"],
        )

        # Snap width and height
        max_width = constraints["width"]["max"]
        max_height = constraints["height"]["max"]

        width = snap_to_increment(
            width,
            constraints["width"]["min"],
            min(max_width, constraints["offset_x"]["max"] - x + 1),
            constraints["width"]["increment"],
        )
        height = snap_to_increment(
            height,
            constraints["height"]["min"],
            min(max_height, constraints["offset_y"]["max"] - y + 1),
            constraints["height"]["increment"],
        )

        return (x, y, width, height)

    def set_config(self, configs: Dict):
        """
        Update camera configuration

        Based on tested implementation from flow-microscopy-platform

        Note: For picamera, framerate and shutter_speed can be safely modified
        while capture_continuous is running (they take effect on next frame).
        However, we avoid clearing cam_running_event here to prevent interrupting
        the capture loop unnecessarily.
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        # Configure AWB and exposure (from tested code)
        self.cam.awb_mode = "auto"
        self.cam.exposure_mode = "off"

        # Update resolution
        if "Height" in configs and configs["Height"]:
            size_list = self.config.get("size", [640, 480])
            if isinstance(size_list, list):
                size_list[1] = int(configs["Height"])
                self.config["size"] = size_list
            del configs["Height"]
        if "Width" in configs and configs["Width"]:
            size_list = self.config.get("size", [640, 480])
            if isinstance(size_list, list):
                size_list[0] = int(configs["Width"])
                self.config["size"] = size_list
            del configs["Width"]

        size_config = self.config.get("size", [640, 480])
        if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
            self.cam.resolution = (int(size_config[0]), int(size_config[1]))
        else:
            self.cam.resolution = (640, 480)

        # Update framerate (safe to set while capture_continuous is running)
        if "FrameRate" in configs and configs["FrameRate"]:
            self.config["FrameRate"] = int(configs["FrameRate"])
            self.frame_rate = int(configs["FrameRate"])
            del configs["FrameRate"]
        framerate = self.config.get("FrameRate", 30)
        if isinstance(framerate, (int, float)):
            self.cam.framerate = int(framerate)

        # Update shutter speed (safe to set while capture_continuous is running)
        if "ShutterSpeed" in configs and configs["ShutterSpeed"]:
            self.config["ShutterSpeed"] = int(configs["ShutterSpeed"])
            del configs["ShutterSpeed"]
        shutter = self.config.get("ShutterSpeed", 10000)
        if isinstance(shutter, (int, float)):
            self.cam.shutter_speed = int(shutter)

    def get_actual_framerate(self) -> float:
        """
        Get actual framerate from camera hardware.

        Returns the actual framerate that the camera is using, which may differ
        from the configured value due to hardware limitations or rounding.

        Returns:
            float: Actual framerate in FPS
        """
        if self.cam is None:
            return float(self.config.get("FrameRate", 30))
        try:
            return float(self.cam.framerate)
        except (AttributeError, ValueError):
            return float(self.config.get("FrameRate", 30))

    def get_actual_shutter_speed(self) -> int:
        """
        Get actual shutter speed from camera hardware.

        Returns the actual shutter speed that the camera is using (in microseconds),
        which may differ from the configured value due to hardware limitations.

        Returns:
            int: Actual shutter speed in microseconds
        """
        if self.cam is None:
            return int(self.config.get("ShutterSpeed", 10000))
        try:
            return int(self.cam.shutter_speed)
        except (AttributeError, ValueError):
            return int(self.config.get("ShutterSpeed", 10000))

    def capture_frame_at_resolution(self, width: int, height: int) -> bytes:
        """
        Capture a single frame at specified resolution (for snapshots).

        Temporarily reconfigures camera to specified resolution, captures frame,
        then restores original configuration.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels

        Returns:
            bytes: JPEG-encoded frame data
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        import io

        # Save current configuration
        original_resolution = self.cam.resolution
        original_config = self.config.copy()

        try:
            # Temporarily set resolution
            self.cam.resolution = (int(width), int(height))

            # Capture frame as JPEG
            stream = io.BytesIO()
            self.cam.capture(
                stream, format="jpeg", use_video_port=False, quality=CAMERA_SNAPSHOT_JPEG_QUALITY
            )
            stream.seek(0)
            frame_data = stream.read()

            return frame_data
        finally:
            # Restore original resolution and config
            self.cam.resolution = original_resolution
            self.config = original_config
            # Re-apply config settings (AWB, exposure, etc.)
            self.cam.awb_mode = "auto"
            self.cam.exposure_mode = "off"
            if "FrameRate" in original_config:
                self.cam.framerate = int(original_config["FrameRate"])
            if "ShutterSpeed" in original_config:
                self.cam.shutter_speed = int(original_config["ShutterSpeed"])

    def close(self) -> None:
        """Cleanup and close camera"""
        if self.cam:
            self.cam_running_event.clear()
            self.stop()
            self.cam.close()
            self.cam = None

    def list_features(self) -> list:
        """
        List available camera features for UI

        Based on tested implementation from flow-microscopy-platform
        """
        return [
            {
                "name": "Height",
                "display_name": "Height",
                "tooltip": "Height of the video",
                "description": "Height of the video",
                "type": "int",
                "unit": "pixels",
                "range": (1, 2464),
                "access_mode": (True, True),
                "value": self.config["size"][1],
            },
            {
                "name": "Width",
                "display_name": "Width",
                "tooltip": "Width of the video",
                "description": "Width of the video",
                "type": "int",
                "unit": "pixels",
                "range": (1, 3280),
                "access_mode": (True, True),
                "value": self.config["size"][0],
            },
            {
                "name": "FrameRate",
                "display_name": "Frame Rate",
                "tooltip": "Frame Rate of the video",
                "description": "Frame Rate of the video",
                "type": "int",
                "unit": "fps",
                "range": (1, 206),
                "access_mode": (True, True),
                "value": self.config["FrameRate"],
            },
            {
                "name": "ShutterSpeed",
                "display_name": "Exposure",
                "tooltip": "Shutter speed in microseconds",
                "description": "Shutter speed in microseconds",
                "type": "int",
                "unit": "μs",
                "range": (1, 10_000_000),
                "access_mode": (True, True),
                "value": self.config["ShutterSpeed"],
            },
            {
                "name": "AWSMode",
                "display_name": "Auto White Balance",
                "tooltip": "Auto White Balance",
                "description": "Auto White Balance",
                "type": "bool",
                "access_mode": (True, True),
                "value": True,
            },
            {
                "name": "ExposureMode",
                "display_name": "Exposure Mode",
                "tooltip": "Exposure Mode",
                "description": "Exposure Mode",
                "type": "str",
                "access_mode": (True, True),
                "value": "off",
            },
        ]
