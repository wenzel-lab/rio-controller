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

                            # Encode as JPEG
                            _, buffer = cv2.imencode(".jpg", opencv_image)

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
        Get ROI frame using software cropping

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            numpy.ndarray: ROI frame as RGB numpy array
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        x, y, width, height = roi

        # Capture full frame
        frame = self.get_frame_array()

        # Crop ROI: frame[y:y+h, x:x+w]
        roi_frame = frame[y : y + height, x : x + width]

        return roi_frame

    def setup_camera(self, config: Optional[Dict] = None):
        """
        Setup camera configuration

        Based on tested implementation from flow-microscopy-platform
        """
        if self.cam is None or not config:
            return

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
        except Exception:
            pass

    def _add_feature_flags(self, feature_dict: Dict, feature) -> None:
        """Add feature flags if available."""
        try:
            feature_dict["flags"] = feature.get_flags()
        except Exception:
            pass
