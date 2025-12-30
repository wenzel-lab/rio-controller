"""
PiCamera V2 Implementation (64-bit)
Based on tested PiCamera code from flow-microscopy-platform

Uses picamera2 library for 64-bit Raspberry Pi OS
"""

from picamera2 import Picamera2
import cv2
import time
from typing import Optional, Dict, Tuple, Generator, Any
import numpy as np
from queue import Queue
from threading import Event
import logging

from .camera_base import BaseCamera

# Import JPEG quality configuration
try:
    from config import CAMERA_STREAMING_JPEG_QUALITY
except ImportError:
    # Fallback if config not available
    CAMERA_STREAMING_JPEG_QUALITY = 75

logger = logging.getLogger(__name__)


class PiCameraV2(BaseCamera):
    """
    Raspberry Pi Camera implementation for 64-bit OS

    Uses picamera2 library (modern, libcamera-based)
    Based on tested code from flow-microscopy-platform/module-user_interface/webapp/plugins/devices/pi_camera/core.py
    """

    def __init__(self):
        super().__init__()

        # Initialize threading components (from tested code)
        self.cam_running_event: Event = Event()
        self.capture_flag: Event = Event()
        self.capture_queue: Queue[bytes] = Queue(1)

        # Initialize camera (from tested code pattern)
        # Initialize camera - removed WERKZEUG_RUN_MAIN check as it prevents initialization
        # when running python main.py directly (not through Werkzeug reloader)
        self.cam: Optional[Picamera2] = None
        try:
            self.cam = Picamera2()
        except Exception as e:
            logger.error(f"Failed to initialize Picamera2: {e}")
            self.cam = None

        # Default configuration (from tested code)
        self.config = {
            "size": [640, 480],
            "ExposureTime": 10000,
            "FrameRate": 30,
        }
        self.frame_rate = 30

        # Hardware ROI state (for picamera2 sensor crop)
        self.hardware_roi = None  # (x, y, width, height) in sensor coordinates
        self.sensor_size = None  # (width, height) - will be queried from camera

    def start(self) -> None:
        """Start camera"""
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        if not self.cam.started:
            # Configure camera (from tested code)
            size_config = self.config.get("size", [640, 480])
            if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
                size_tuple = (int(size_config[0]), int(size_config[1]))
            else:
                size_tuple = (640, 480)
            self.cam.configure(self.cam.create_video_configuration(main={"size": size_tuple}))
            self.cam.set_controls({"FrameRate": self.config["FrameRate"]})
            self.cam.start()

    def stop(self) -> None:
        """Stop camera"""
        if self.cam and self.cam.started:
            self.cam.stop()
        self.cam_running_event.clear()

    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        """
        Generate frames (generator) - for streaming

        Based on tested implementation from flow-microscopy-platform
        Returns JPEG-encoded frames for web streaming
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        self.cam_running_event.clear()
        self.stop()  # Ensure clean state

        # Configure camera (from tested code)
        size_config = self.config.get("size", [640, 480])
        if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
            size_tuple = (int(size_config[0]), int(size_config[1]))
        else:
            size_tuple = (640, 480)
        self.cam.configure(self.cam.create_video_configuration(main={"size": size_tuple}))
        framerate = self.config.get("FrameRate", 30)
        if isinstance(framerate, (int, float)):
            self.cam.set_controls({"FrameRate": int(framerate)})
        self.cam.start()

        self.cam_running_event.set()
        framerate_val = self.config.get("FrameRate", 30)
        if isinstance(framerate_val, (int, float)):
            frame_interval = 1.0 / float(framerate_val)
        else:
            frame_interval = 1.0 / 30.0

        while self.cam_running_event.is_set():
            start_time = time.time()

            # Call frame callback if set (for strobe trigger)
            if self.frame_callback:
                self.frame_callback()

            # Capture frame as numpy array (from tested code)
            frame = self.cam.capture_array()
            # picamera2 returns BGR, convert to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Encode as JPEG with streaming quality (lower quality for reduced bandwidth/CPU)
            ret, buffer = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, CAMERA_STREAMING_JPEG_QUALITY]
            )

            # Handle capture request
            if self.capture_flag.is_set():
                self.capture_queue.put(buffer)
                self.capture_flag.clear()

            yield buffer.tobytes()

            # Ensure frame rate is respected (from tested code)
            elapsed_time = time.time() - start_time
            time.sleep(max(0, frame_interval - elapsed_time))

        self.stop()

    def get_frame_array(self) -> np.ndarray:
        """
        Get single frame as numpy array

        Returns:
            numpy.ndarray: Frame as RGB numpy array
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        if not self.cam.started:
            self.start()

        # Capture frame (from tested code)
        frame = self.cam.capture_array()
        # picamera2 returns BGR, convert to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def capture_frame_at_resolution(self, width: int, height: int) -> bytes:
        """
        Capture a single frame at specified resolution (for snapshots).

        For picamera2, we can capture a still image at any resolution without
        reconfiguring the video stream. Uses still capture mode.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels

        Returns:
            bytes: JPEG-encoded frame data
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        try:
            # Save current configuration state
            was_started = self.cam.started

            # Stop camera if it's running (needed for reconfiguration)
            if was_started:
                self.cam.stop()

            # Create a still configuration at the requested resolution
            still_config = self.cam.create_still_configuration(
                main={"size": (int(width), int(height))}
            )
            self.cam.configure(still_config)
            self.cam.start()

            # Wait a bit for camera to stabilize
            time.sleep(0.1)

            # Capture still image
            request = self.cam.capture_request()
            array = request.make_array("main")
            request.release()

            # Convert numpy array to JPEG (picamera2 returns RGB)
            import io
            from PIL import Image

            img = Image.fromarray(array)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            frame_data = buffer.getvalue()

            # Restore video configuration if camera was running
            if was_started:
                self.cam.stop()
                # Restore video configuration
                size_config = self.config.get("size", [640, 480])
                if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
                    size_tuple = (int(size_config[0]), int(size_config[1]))
                else:
                    size_tuple = (640, 480)
                video_config = self.cam.create_video_configuration(main={"size": size_tuple})
                self.cam.configure(video_config)
                framerate = self.config.get("FrameRate", 30)
                if isinstance(framerate, (int, float)):
                    self.cam.set_controls({"FrameRate": int(framerate)})
                self.cam.start()
                # Reset running event (if it exists)
                if hasattr(self, "cam_running_event"):
                    self.cam_running_event.set()

            return frame_data
        except Exception as e:
            logger.error(f"Error capturing frame at resolution {width}x{height}: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            # Fallback: try to capture at current resolution
            try:
                if not self.cam.started:
                    self.cam.start()
                request = self.cam.capture_request()
                array = request.make_array("main")
                request.release()
                import io
                from PIL import Image

                img = Image.fromarray(array)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=95)
                return buffer.getvalue()
            except Exception as e2:
                logger.error(f"Fallback capture also failed: {e2}")
                raise

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI frame. If hardware ROI is set, returns full frame (which is already ROI).
        Otherwise does software cropping.

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            numpy.ndarray: ROI frame as RGB numpy array

        Note: If hardware ROI was set via set_roi_hardware(), the camera is already
        capturing only the ROI region, so we return the full frame (which is the ROI).
        Otherwise, we do software cropping.
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        if not self.cam.started:
            self.start()

        # Get current frame (if hardware ROI is set, this is already the ROI region)
        frame = self.cam.capture_array()
        # picamera2 returns BGR, convert to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # If hardware ROI was applied successfully, return the frame as-is.
        if self.hardware_roi:
            return frame

        # Otherwise perform software crop
        x, y, width, height = roi
        roi_frame = frame[y : y + height, x : x + width]
        return roi_frame

    def set_roi_hardware(self, roi: Tuple[int, int, int, int]) -> bool:
        """
        Set hardware ROI on Pi camera using picamera2 sensor crop.

        Args:
            roi: (x, y, width, height) tuple in pixels

        Returns:
            bool: True if hardware ROI was set successfully, False otherwise

        Note:
            This uses picamera2's ScalerCrop control to set sensor-level ROI.
            The camera will only capture the specified region.
            To reset to full frame, set ROI to (0, 0, sensor_width, sensor_height).
        """
        if self.cam is None:
            return False

        x, y, width, height = roi

        try:
            # Get sensor size if not already known
            if self.sensor_size is None:
                # Query sensor size from camera
                sensor_modes = self.cam.sensor_modes
                if sensor_modes:
                    # Get the active or first sensor mode
                    mode = sensor_modes[0] if sensor_modes else None
                    if mode and "size" in mode:
                        self.sensor_size = tuple(mode["size"])
                    else:
                        # Fallback: use maximum known sensor sizes
                        # HQ Camera: 4056×3040, V2 Camera: 3280×2464
                        # Try to detect by checking available modes
                        max_w, max_h = 0, 0
                        for mode in sensor_modes:
                            if "size" in mode:
                                w, h = mode["size"]
                                if w > max_w:
                                    max_w = w
                                if h > max_h:
                                    max_h = h
                        if max_w > 0 and max_h > 0:
                            self.sensor_size = (max_w, max_h)
                        else:
                            # Default fallback
                            self.sensor_size = (3280, 2464)  # V2 Camera default
                else:
                    self.sensor_size = (3280, 2464)  # Default fallback

            sensor_width, sensor_height = self.sensor_size

            # Convert pixel coordinates to normalized coordinates (0.0-1.0)
            # ScalerCrop uses (x, y, width, height) in normalized coordinates
            norm_x = x / sensor_width
            norm_y = y / sensor_height
            norm_w = width / sensor_width
            norm_h = height / sensor_height

            # Clamp to valid range
            norm_x = max(0.0, min(1.0, norm_x))
            norm_y = max(0.0, min(1.0, norm_y))
            norm_w = max(0.0, min(1.0 - norm_x, norm_w))
            norm_h = max(0.0, min(1.0 - norm_y, norm_h))

            # Stop camera before reconfiguring
            was_started = self.cam.started
            if was_started:
                self.cam.stop()

            # Set ScalerCrop control for hardware ROI
            # ScalerCrop: (x, y, width, height) in normalized coordinates (0.0-1.0)
            # This is the picamera2 equivalent of rpicam-apps --roi parameter
            # According to official Raspberry Pi docs: HQ Camera supports hardware ROI
            # via normalized coordinates, same as our implementation
            try:
                self.cam.set_controls({"ScalerCrop": (norm_x, norm_y, norm_w, norm_h)})
            except Exception as e:
                # If set_controls fails, try setting during configuration
                logger.debug(f"set_controls ScalerCrop failed, trying configuration method: {e}")
                size_config = self.config.get("size", [640, 480])
                if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
                    size_tuple = (int(size_config[0]), int(size_config[1]))
                else:
                    size_tuple = (640, 480)
                video_config = self.cam.create_video_configuration(main={"size": size_tuple})
                video_config["controls"]["ScalerCrop"] = (norm_x, norm_y, norm_w, norm_h)
                self.cam.configure(video_config)

            # Restart camera if it was running
            if was_started:
                self.cam.start()

            # Store hardware ROI state
            self.hardware_roi = (x, y, width, height)
            logger.info(
                f"Hardware ROI set on Pi camera: {roi} (normalized: {norm_x:.3f}, {norm_y:.3f}, {norm_w:.3f}, {norm_h:.3f})"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to set hardware ROI on Pi camera: {e}")
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
            # Query sensor modes to find maximum resolution
            sensor_modes = self.cam.sensor_modes
            if sensor_modes:
                max_w, max_h = 0, 0
                for mode in sensor_modes:
                    if "size" in mode:
                        w, h = mode["size"]
                        if w > max_w:
                            max_w = w
                        if h > max_h:
                            max_h = h
                if max_w > 0 and max_h > 0:
                    return (max_w, max_h)
        except Exception:
            pass

        # Default fallback (V2 Camera)
        return (3280, 2464)

    def get_roi_constraints(self) -> Dict[str, Any]:
        """
        Get ROI constraints for Pi camera (min, max, increment values)

        Returns:
            Dict with keys: offset_x, offset_y, width, height
            Each contains: min, max, increment, current
        """
        max_width, max_height = self.get_max_resolution()

        # Pi cameras typically support arbitrary ROI with 1-pixel increments
        # But ScalerCrop uses normalized coordinates, so we work in pixels
        constraints = {
            "offset_x": {"min": 0, "max": max_width, "increment": 1, "current": 0},
            "offset_y": {"min": 0, "max": max_height, "increment": 1, "current": 0},
            "width": {"min": 10, "max": max_width, "increment": 1, "current": max_width},
            "height": {"min": 10, "max": max_height, "increment": 1, "current": max_height},
        }

        # Update current values if hardware ROI is set
        if self.hardware_roi:
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

        # Snap width and height, ensuring they fit within sensor bounds
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

    def get_actual_framerate(self) -> float:
        """
        Get actual framerate from camera hardware.

        Returns the actual framerate that the camera is using, which may differ
        from the configured value due to hardware limitations or rounding.

        Note: picamera2 typically respects the configured framerate, so we return
        the config value. For more accurate readback, could query camera controls.

        Returns:
            float: Actual framerate in FPS
        """
        if self.cam is None:
            return float(self.config.get("FrameRate", 30))
        try:
            # picamera2 uses controls dictionary - framerate is set via configuration
            # Return configured framerate (picamera2 typically respects what we set)
            return float(self.config.get("FrameRate", 30))
        except (AttributeError, ValueError):
            return float(self.config.get("FrameRate", 30))

    def get_actual_shutter_speed(self) -> int:
        """
        Get actual shutter speed from camera hardware.

        Returns the actual shutter speed that the camera is using (in microseconds),
        which may differ from the configured value due to hardware limitations.

        Note: picamera2 may round shutter speed to supported values. For more accurate
        readback, could query camera controls, but config value is usually sufficient.

        Returns:
            int: Actual shutter speed in microseconds
        """
        if self.cam is None:
            return int(self.config.get("ShutterSpeed", 10000))
        try:
            # picamera2 uses controls - return configured value
            # (picamera2 may round to supported values, but config is usually accurate)
            return int(self.config.get("ShutterSpeed", 10000))
        except (AttributeError, ValueError):
            return int(self.config.get("ShutterSpeed", 10000))

    def set_config(self, configs: Dict):
        """
        Update camera configuration

        Based on tested implementation from flow-microscopy-platform
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        self.cam_running_event.clear()
        self.stop()  # Stop before reconfiguring

        # Update resolution
        if "Height" in configs:
            size_list = self.config.get("size", [640, 480])
            if isinstance(size_list, list):
                size_list[1] = int(configs["Height"])
                self.config["size"] = size_list
            del configs["Height"]
        if "Width" in configs:
            size_list = self.config.get("size", [640, 480])
            if isinstance(size_list, list):
                size_list[0] = int(configs["Width"])
                self.config["size"] = size_list
            del configs["Width"]

        # Update other config values (from tested code)
        for key, value in configs.items():
            if isinstance(value, str) and value.isdigit():
                value = int(value)
                configs[key] = value
                self.config[key] = value

        # Reconfigure camera (from tested code)
        size_config = self.config.get("size", [640, 480])
        if isinstance(size_config, (list, tuple)) and len(size_config) >= 2:
            size_tuple = (int(size_config[0]), int(size_config[1]))
        else:
            size_tuple = (640, 480)
        self.cam.configure(self.cam.create_video_configuration(main={"size": size_tuple}))
        self.cam.set_controls(configs)

        # Update frame rate if specified
        if "FrameRate" in configs:
            self.frame_rate = configs["FrameRate"]

    def close(self):
        """Cleanup and close camera"""
        if self.cam:
            self.cam_running_event.clear()
            self.stop()
            self.cam.close()
            self.cam = None

    def _get_size_value(self, index: int, default: int) -> int:
        """Get size value from config safely."""
        size_config = self.config.get("size", [640, 480])
        if isinstance(size_config, (list, tuple)) and len(size_config) > index:
            return int(size_config[index])
        return default

    def list_features(self) -> list:
        """
        List available camera features for UI

        Note: picamera2 has dynamic features, but for now return basic set
        Can be extended to query actual camera features
        """
        return [
            {
                "name": "Height",
                "display_name": "Height",
                "tooltip": "Height of the video",
                "description": "Height of the video",
                "type": "int",
                "unit": "pixels",
                "range": (1, 3040),  # HQ Camera max
                "access_mode": (True, True),
                "value": self._get_size_value(1, 480),
            },
            {
                "name": "Width",
                "display_name": "Width",
                "tooltip": "Width of the video",
                "description": "Width of the video",
                "type": "int",
                "unit": "pixels",
                "range": (1, 4056),  # HQ Camera max
                "access_mode": (True, True),
                "value": self._get_size_value(0, 640),
            },
            {
                "name": "FrameRate",
                "display_name": "Frame Rate",
                "tooltip": "Frame Rate of the video",
                "description": "Frame Rate of the video",
                "type": "int",
                "unit": "fps",
                "range": (1, 120),
                "access_mode": (True, True),
                "value": self.config["FrameRate"],
            },
            {
                "name": "ExposureTime",
                "display_name": "Exposure Time",
                "tooltip": "Exposure time in microseconds",
                "description": "Exposure time in microseconds",
                "type": "int",
                "unit": "μs",
                "range": (1, 10_000_000),
                "access_mode": (True, True),
                "value": self.config.get("ExposureTime", 10000),
            },
        ]
