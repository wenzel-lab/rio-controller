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
            if PiCamera is None or not callable(PiCamera):
                raise RuntimeError("PiCamera class unavailable (picamera import failed)")
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
        # Cumulative picamera zoom window in normalized sensor coords (0..1).
        # Nested Apply ROI composes into this; Clear resets to full frame.
        self._norm_crop: Optional[Tuple[float, float, float, float]] = None
        self.hardware_roi: Optional[Tuple[int, int, int, int]] = None

        # Hardware H.264 recording on splitter port 1 (JPEG stream uses port 0)
        self._h264_record_port: Optional[int] = None
        self._h264_path: Optional[str] = None
        # Decode JPEG→numpy only when a consumer needs ROI arrays (droplet, etc.).
        # Always-on decode at 1024×768 saturates the Pi CPU and freezes the preview.
        self._roi_decode_enabled: bool = False

    def set_roi_decode_enabled(self, enabled: bool) -> None:
        """Enable/disable per-frame JPEG decode for get_frame_roi / droplet."""
        self._roi_decode_enabled = bool(enabled)

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
        """Stop camera recording / streaming helpers"""
        if self.cam and self.cam.recording:
            try:
                port = self._h264_record_port if self._h264_record_port is not None else 1
                self.cam.stop_recording(splitter_port=port)
            except Exception as e:
                logger.debug("stop_recording during stop(): %s", e)
            self._h264_record_port = None
            self._h264_path = None
        self.cam_running_event.clear()

    def start_h264_recording(
        self,
        path: str,
        splitter_port: int = 1,
        bitrate: int = 8_000_000,
    ) -> str:
        """
        Start hardware H.264 recording on a splitter port.

        Official picamera pattern (recipes2 / multi-res recording):
        - JPEG / capture_continuous uses splitter_port=0 (use_video_port=True)
        - H.264 recording uses splitter_port=1 (default) so both run together

        See: https://picamera.readthedocs.io/en/latest/recipes2.html#recording-at-multiple-resolutions
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")
        if splitter_port == 0:
            raise ValueError("splitter_port 0 is reserved for JPEG streaming")
        if self.cam.recording:
            raise RuntimeError("Camera is already recording")

        # Ensure framerate matches config so timestamps are correct
        framerate = self.config.get("FrameRate", self.frame_rate or 30)
        try:
            self.cam.framerate = int(framerate)
        except Exception as e:
            logger.debug("Could not set framerate before recording: %s", e)

        self.cam.start_recording(
            path,
            format="h264",
            splitter_port=int(splitter_port),
            bitrate=int(bitrate),
        )
        self._h264_record_port = int(splitter_port)
        self._h264_path = path
        logger.info(
            "H.264 recording started on splitter_port=%s → %s",
            splitter_port,
            path,
        )
        return path

    def stop_h264_recording(self) -> Optional[str]:
        """Stop hardware H.264 recording; returns the .h264 path if any."""
        if self.cam is None:
            return None
        path = self._h264_path
        port = self._h264_record_port if self._h264_record_port is not None else 1
        if self.cam.recording:
            try:
                self.cam.stop_recording(splitter_port=port)
                logger.info("H.264 recording stopped (port=%s): %s", port, path)
            except Exception as e:
                logger.error("Error stopping H.264 recording: %s", e)
                raise
        self._h264_record_port = None
        self._h264_path = None
        return path

    def is_h264_recording(self) -> bool:
        """True if hardware H.264 recording is active."""
        return bool(self.cam is not None and self.cam.recording and self._h264_path)

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
            stream,
            format="jpeg",
            use_video_port=True,
            splitter_port=0,
            quality=CAMERA_STREAMING_JPEG_QUALITY,
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

            # Decode JPEG→RGB only when droplet/ROI consumers need arrays.
            # Scenario 1 (droplet off) skips this — major source of ~1–2s freezes on Pi.
            if self._roi_decode_enabled:
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
            # Software ROI cropping when the frame is not already at the hardware ROI size
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

    def set_roi_hardware(self, roi: Tuple[int, int, int, int], absolute: bool = False) -> bool:
        """
        Set hardware ROI on Pi camera using picamera's crop property.

        Args:
            roi: (x, y, width, height) tuple in pixels
            absolute: If True, coords are in the capture-frame pixel space and
                replace the zoom window from the full sensor. If False, coords
                are view-relative to the current zoomed frame and nest inside
                the existing crop (successive Apply ROI without Clear).

        Returns:
            bool: True if hardware ROI was set successfully, False otherwise
        """
        if self.cam is None:
            return False

        x, y, width, height = roi

        try:
            res_w, res_h = self.cam.resolution
            res_w = max(1, int(res_w))
            res_h = max(1, int(res_h))

            if self._norm_crop is None:
                self._norm_crop = (0.0, 0.0, 1.0, 1.0)

            if absolute:
                # Capture-frame absolute → full-sensor normalized crop (replaces).
                nx = x / float(res_w)
                ny = y / float(res_h)
                nw = width / float(res_w)
                nh = height / float(res_h)
                self._norm_crop = (
                    max(0.0, min(1.0, nx)),
                    max(0.0, min(1.0, ny)),
                    max(0.0, min(1.0, nw)),
                    max(0.0, min(1.0, nh)),
                )
            else:
                # View-relative nest inside the current zoom window.
                cx, cy, cw, ch = self._norm_crop
                nx = cx + (x / float(res_w)) * cw
                ny = cy + (y / float(res_h)) * ch
                nw = (width / float(res_w)) * cw
                nh = (height / float(res_h)) * ch
                self._norm_crop = (
                    max(0.0, min(1.0, nx)),
                    max(0.0, min(1.0, ny)),
                    max(0.0, min(1.0, nw)),
                    max(0.0, min(1.0, nh)),
                )

            # Keep crop inside the sensor and non-empty.
            cx, cy, cw, ch = self._norm_crop
            cw = max(1e-4, min(cw, 1.0 - cx))
            ch = max(1e-4, min(ch, 1.0 - cy))
            self._norm_crop = (cx, cy, cw, ch)

            self.cam.crop = self._norm_crop

            # Pixel ROI in capture-frame space (for constraints / UI absolute mode).
            self.hardware_roi = (
                int(round(cx * res_w)),
                int(round(cy * res_h)),
                max(1, int(round(cw * res_w))),
                max(1, int(round(ch * res_h))),
            )
            logger.info(
                "Hardware ROI set on Pi camera (legacy): roi=%s absolute=%s "
                "norm_crop=(%.4f, %.4f, %.4f, %.4f) hardware_roi=%s",
                roi,
                absolute,
                cx,
                cy,
                cw,
                ch,
                self.hardware_roi,
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to set hardware ROI on Pi camera (legacy): {e}")
            self.hardware_roi = None
            return False

    def get_stream_size(self) -> Tuple[int, int]:
        """Actual JPEG frame size (picamera crop zooms content; resolution stays)."""
        if self.cam is None:
            size = self.config.get("size", [640, 480])
            return int(size[0]), int(size[1])
        try:
            w, h = self.cam.resolution
            return int(w), int(h)
        except Exception:
            size = self.config.get("size", [640, 480])
            return int(size[0]), int(size[1])

    def reset_to_resolution(self, width: int, height: int) -> None:
        """Clear hardware crop and restore full-frame capture (Clear ROI)."""
        if self.cam is None:
            return
        try:
            # Full sensor zoom window (picamera normalized crop).
            self.cam.crop = (0.0, 0.0, 1.0, 1.0)
            self._norm_crop = (0.0, 0.0, 1.0, 1.0)
            self.hardware_roi = None
            w = max(16, int(width))
            h = max(16, int(height))
            try:
                self.cam.resolution = (w, h)
                self.config["size"] = [w, h]
            except Exception as exc:
                logger.debug("Pi resolution restore after ROI clear failed: %s", exc)
            logger.info("Pi camera hardware ROI cleared → full frame (%sx%s)", w, h)
        except Exception as e:
            logger.warning("Failed to clear Pi camera hardware ROI: %s", e)

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
