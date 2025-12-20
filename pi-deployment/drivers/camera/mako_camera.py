"""
MAKO Camera Implementation
Based on tested MakoCamera code from flow-microscopy-platform

Uses Vimba library for Allied Vision MAKO cameras
"""

import cv2
from typing import Optional, Dict, Tuple, Generator, Any, List
import numpy as np
from queue import Queue
from threading import Event

from .camera_base import BaseCamera

# Import JPEG quality configuration
try:
    from config import CAMERA_STREAMING_JPEG_QUALITY
except ImportError:
    # Fallback if config not available
    CAMERA_STREAMING_JPEG_QUALITY = 75

try:
    from vimba import (
        Vimba,
        Camera,
        Frame,
        VimbaCameraError,
        VimbaFeatureError,
    )

    VIMBA_AVAILABLE = True
except ImportError:
    VIMBA_AVAILABLE = False
    Camera = None
    Frame = None


class MakoCamera(BaseCamera):
    """
    MAKO Camera implementation using Vimba library

    Based on tested code from flow-microscopy-platform/module-user_interface/webapp/plugins/devices/mako_camera/core.py
    """

    def __init__(self, cam_id: Optional[str] = None):
        super().__init__()

        if not VIMBA_AVAILABLE:
            raise RuntimeError(
                "Vimba library not available. Install with: pip install vimba-python"
            )

        self.cam_id = cam_id
        self.cam: Optional[Camera] = None

        # Initialize threading components (from tested code)
        self.cam_running_event: Event = Event()
        self.capture_flag: Event = Event()
        self.capture_queue: Queue[bytes] = Queue(1)

        # Get camera instance
        with Vimba.get_instance():
            self.cam = self.get_camera(self.cam_id)
            if self.cam is None:
                raise RuntimeError("Failed to initialize MAKO camera")

    def get_camera(self, cam_id: Optional[str] = None) -> Optional[Camera]:
        """
        Get camera instance by ID or first available

        Based on tested implementation from flow-microscopy-platform
        """
        try:
            with Vimba.get_instance() as vimba:
                if cam_id:
                    try:
                        return vimba.get_camera_by_id(cam_id)
                    except VimbaCameraError:
                        print(f"Failed to access Camera '{cam_id}'. Abort.")
                        return None
                else:
                    cams = vimba.get_all_cameras()
                    if not cams:
                        print("No MAKO cameras accessible. Abort.")
                        return None
                    return cams[0]
        except Exception as e:
            print(f"Error getting MAKO camera: {e}")
            return None

    def start(self) -> None:
        """Start camera"""
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        # Camera is started when generate_frames is called
        pass

    def stop(self) -> None:
        """Stop camera"""
        self.cam_running_event.clear()
        if self.cam:
            try:
                self.cam.stop_streaming()
            except Exception:
                pass

    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        """
        Generate frames (generator) - for streaming

        Based on tested implementation from flow-microscopy-platform
        Returns JPEG-encoded frames for web streaming
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        try:
            with Vimba.get_instance():
                with self.cam:
                    self.setup_camera(config)
                    self.cam_running_event.set()

                    try:
                        while self.cam_running_event.is_set():
                            # Call frame callback if set (for strobe trigger)
                            if self.frame_callback:
                                self.frame_callback()

                            # Get frame (from tested code)
                            frame: Frame = self.cam.get_frame()

                            # Convert to OpenCV image (from tested code)
                            opencv_image = frame.as_opencv_image()

                            # Encode as JPEG with streaming quality (lower quality for reduced bandwidth/CPU)
                            _, buffer = cv2.imencode(
                                ".jpg", opencv_image,
                                [cv2.IMWRITE_JPEG_QUALITY, CAMERA_STREAMING_JPEG_QUALITY]
                            )

                            # Handle capture request
                            if self.capture_flag.is_set():
                                self.capture_queue.put(buffer)
                                self.capture_flag.clear()

                            yield buffer.tobytes()
                    finally:
                        self.stop()
        except VimbaCameraError as e:
            print(f"MAKO camera error: {e}")
            yield b""

    def get_frame_array(self) -> np.ndarray:
        """
        Get single frame as numpy array

        Returns:
            numpy.ndarray: Frame as RGB numpy array
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        with Vimba.get_instance():
            with self.cam:
                frame: Frame = self.cam.get_frame()
                opencv_image = frame.as_opencv_image()
                # Vimba returns BGR, convert to RGB
                rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
                return rgb_image

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI frame. If hardware ROI is already set, returns full frame (which is already ROI).
        Otherwise does software cropping.

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            numpy.ndarray: ROI frame as RGB numpy array

        Note:
            If hardware ROI was set via set_roi_hardware(), the camera is already
            capturing only the ROI region, so we return the full frame (which is the ROI).
            Otherwise, we do software cropping.
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        # Get current frame (if hardware ROI is set, this is already the ROI region)
        frame = self.get_frame_array()

        # Check if hardware ROI is active by comparing frame size to expected ROI
        x, y, width, height = roi
        frame_height, frame_width = frame.shape[:2]

        # If frame size matches ROI size (within tolerance), hardware ROI is likely active
        if abs(frame_width - width) <= 2 and abs(frame_height - height) <= 2:
            # Hardware ROI is active, return frame as-is
            return frame
        else:
            # Hardware ROI not active, do software cropping
            roi_frame = frame[y : y + height, x : x + width]
            return roi_frame

    def set_roi_hardware(self, roi: Tuple[int, int, int, int]) -> bool:
        """
        Set hardware ROI on Mako camera using OffsetX, OffsetY, Width, Height

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            bool: True if hardware ROI was set successfully, False otherwise

        Note:
            This changes the camera's global ROI settings. The camera will only
            capture the specified region. To reset to full frame, set ROI to
            (0, 0, max_width, max_height).
        """
        if self.cam is None:
            return False

        x, y, width, height = roi

        try:
            with Vimba.get_instance():
                with self.cam:
                    # Set ROI offset and size
                    self.cam.OffsetX.set(int(x))
                    self.cam.OffsetY.set(int(y))
                    self.cam.Width.set(int(width))
                    self.cam.Height.set(int(height))
                    return True
        except (VimbaFeatureError, VimbaCameraError) as e:
            print(f"Failed to set hardware ROI on Mako camera: {e}")
            return False

    def get_max_resolution(self) -> Tuple[int, int]:
        """
        Get maximum sensor resolution for Mako camera

        Returns:
            Tuple[int, int]: (max_width, max_height)
        """
        if self.cam is None:
            return (640, 480)  # Default fallback

        try:
            with Vimba.get_instance():
                with self.cam:
                    # Get maximum width/height (sensor size)
                    max_width = self.cam.WidthMax.get()
                    max_height = self.cam.HeightMax.get()
                    return (int(max_width), int(max_height))
        except (VimbaFeatureError, VimbaCameraError):
            return (640, 480)  # Default fallback

    def get_roi_constraints(self) -> Dict[str, Any]:
        """
        Get ROI constraints from Mako camera (min, max, increment values)

        Returns:
            Dict with keys: offset_x, offset_y, width, height
            Each contains: min, max, increment, current
        """
        constraints = {
            "offset_x": {"min": 0, "max": 640, "increment": 1, "current": 0},
            "offset_y": {"min": 0, "max": 480, "increment": 1, "current": 0},
            "width": {"min": 10, "max": 640, "increment": 1, "current": 640},
            "height": {"min": 10, "max": 480, "increment": 1, "current": 480},
        }

        if self.cam is None:
            return constraints

        try:
            with Vimba.get_instance():
                with self.cam:
                    # Query OffsetX constraints
                    try:
                        offset_x_range = self.cam.OffsetX.get_range()
                        constraints["offset_x"]["min"] = int(offset_x_range[0])
                        constraints["offset_x"]["max"] = int(offset_x_range[1])
                        constraints["offset_x"]["current"] = int(self.cam.OffsetX.get())
                        try:
                            constraints["offset_x"]["increment"] = int(
                                self.cam.OffsetX.get_increment()
                            )
                        except Exception:
                            constraints["offset_x"]["increment"] = 1
                    except Exception:
                        pass

                    # Query OffsetY constraints
                    try:
                        offset_y_range = self.cam.OffsetY.get_range()
                        constraints["offset_y"]["min"] = int(offset_y_range[0])
                        constraints["offset_y"]["max"] = int(offset_y_range[1])
                        constraints["offset_y"]["current"] = int(self.cam.OffsetY.get())
                        try:
                            constraints["offset_y"]["increment"] = int(
                                self.cam.OffsetY.get_increment()
                            )
                        except Exception:
                            constraints["offset_y"]["increment"] = 1
                    except Exception:
                        pass

                    # Query Width constraints
                    try:
                        width_range = self.cam.Width.get_range()
                        constraints["width"]["min"] = int(width_range[0])
                        constraints["width"]["max"] = int(width_range[1])
                        constraints["width"]["current"] = int(self.cam.Width.get())
                        try:
                            constraints["width"]["increment"] = int(self.cam.Width.get_increment())
                        except Exception:
                            constraints["width"]["increment"] = 1
                    except Exception:
                        pass

                    # Query Height constraints
                    try:
                        height_range = self.cam.Height.get_range()
                        constraints["height"]["min"] = int(height_range[0])
                        constraints["height"]["max"] = int(height_range[1])
                        constraints["height"]["current"] = int(self.cam.Height.get())
                        try:
                            constraints["height"]["increment"] = int(
                                self.cam.Height.get_increment()
                            )
                        except Exception:
                            constraints["height"]["increment"] = 1
                    except Exception:
                        pass
        except (VimbaFeatureError, VimbaCameraError):
            pass

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

        # Snap to increments
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

        # Ensure ROI doesn't exceed sensor bounds
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

    def setup_camera(self, config: Optional[Dict] = None):
        """
        Setup camera configuration

        Based on tested implementation from flow-microscopy-platform
        Supports hardware ROI via OffsetX, OffsetY, Width, Height
        """
        if self.cam is None or not config:
            return

        # Set ROI offset first (if specified), then width/height
        # This allows hardware ROI support for Mako cameras
        self._set_camera_offset_x(config)
        self._set_camera_offset_y(config)
        self._set_camera_width(config)
        self._set_camera_height(config)
        self._set_camera_framerate(config)

    def _set_camera_width(self, config: Dict) -> None:
        """Set camera width if specified."""
        if "Width" in config and self.cam:
            try:
                self.cam.Width.set(int(config["Width"]))
            except VimbaFeatureError:
                pass

    def _set_camera_height(self, config: Dict) -> None:
        """Set camera height if specified."""
        if "Height" in config and self.cam:
            try:
                self.cam.Height.set(int(config["Height"]))
            except VimbaFeatureError:
                pass

    def _set_camera_offset_x(self, config: Dict) -> None:
        """Set camera X offset (for hardware ROI) if specified."""
        if "OffsetX" in config and self.cam:
            try:
                self.cam.OffsetX.set(int(config["OffsetX"]))
            except VimbaFeatureError:
                pass

    def _set_camera_offset_y(self, config: Dict) -> None:
        """Set camera Y offset (for hardware ROI) if specified."""
        if "OffsetY" in config and self.cam:
            try:
                self.cam.OffsetY.set(int(config["OffsetY"]))
            except VimbaFeatureError:
                pass

    def _set_camera_framerate(self, config: Dict) -> None:
        """Set camera framerate if specified."""
        if "FrameRate" in config and self.cam:
            try:
                self.cam.AcquisitionFrameRate.set(float(config["FrameRate"]))
            except VimbaFeatureError:
                pass

    def set_config(self, configs: Dict):
        """
        Update camera configuration
        """
        # Configuration is applied in setup_camera
        self.config.update(configs)

    def close(self):
        """Cleanup and close camera"""
        self.stop()
        self.cam = None

    def list_features(self) -> List[Dict[str, Any]]:
        """
        List available camera features for UI

        Based on tested implementation from flow-microscopy-platform
        """
        features: List[Dict[str, Any]] = []
        if self.cam is None:
            return features

        try:
            with Vimba.get_instance():
                with self.cam:
                    for feature in self.cam.get_all_features():
                        feature_dict = self._process_feature(feature)
                        if feature_dict:
                            features.append(feature_dict)
        except VimbaCameraError:
            pass

        return features

    def _process_feature(self, feature) -> Optional[Dict]:
        """Process a single camera feature into a dictionary."""
        try:
            feature_dict = {
                "name": feature.get_name(),
                "display_name": feature.get_display_name(),
                "tooltip": feature.get_tooltip(),
                "description": feature.get_description(),
                "type": str(feature.get_type()),
                "access_mode": feature.get_access_mode(),
            }
            self._add_feature_value(feature_dict, feature)
            self._add_feature_range(feature_dict, feature)
            self._add_feature_flags(feature_dict, feature)
            return feature_dict
        except Exception:
            return None

    def _add_feature_value(self, feature_dict: Dict, feature) -> None:
        """Add feature value if available."""
        try:
            feature_dict["value"] = feature.get()
        except Exception:
            pass

    def _add_feature_range(self, feature_dict: Dict, feature) -> None:
        """Add feature range if available."""
        try:
            feature_dict["range"] = feature.get_range()
            # Also get increment if available (important for ROI alignment)
            try:
                feature_dict["increment"] = feature.get_increment()
            except Exception:
                pass
        except Exception:
            pass

    def _add_feature_flags(self, feature_dict: Dict, feature) -> None:
        """Add feature flags if available."""
        try:
            feature_dict["flags"] = feature.get_flags()
        except Exception:
            pass
