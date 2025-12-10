"""
PiCamera Legacy Implementation (32-bit)
Based on tested PiCamera32 code from flow-microscopy-platform

Uses picamera library for 32-bit Raspberry Pi OS
"""

from picamera import PiCamera
import os
import io
import time
from typing import Optional, Dict, Tuple, Generator, Any
import numpy as np
from queue import Queue
from threading import Event

from .camera_base import BaseCamera


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

        # Initialize camera (from tested code pattern)
        self.cam: Optional[PiCamera] = None
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            try:
                self.cam = PiCamera()
            except Exception as e:
                print(f"Failed to initialize PiCamera: {e}")
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

        while self.cam_running_event.is_set():
            start_time = time.time()

            # Call frame callback if set (for strobe trigger)
            if self.frame_callback:
                self.frame_callback()

            # Capture frame as JPEG (from tested code)
            stream = io.BytesIO()
            for _ in self.cam.capture_continuous(stream, "jpeg", use_video_port=True):
                stream.seek(0)
                data = np.frombuffer(stream.getvalue(), dtype=np.uint8)
                stream.truncate(0)
                break

            buffer = data

            # Handle capture request
            if self.capture_flag.is_set():
                self.capture_queue.put(buffer)
                self.capture_flag.clear()

            yield buffer

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

        # Use capture_array() for numpy output
        frame = self.cam.capture_array()
        # picamera returns RGB, so no conversion needed
        return frame

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI frame using picamera's hardware crop feature

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            numpy.ndarray: ROI frame as RGB numpy array

        Note: picamera supports hardware ROI via crop property,
        which is more efficient than software cropping
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        x, y, width, height = roi

        # Save current crop if not already saved
        if self._original_crop is None:
            self._original_crop = self.cam.crop

        # Set ROI crop (picamera uses normalized coordinates 0.0-1.0)
        # Get current resolution for normalization
        current_res = self.cam.resolution
        norm_x = x / current_res[0]
        norm_y = y / current_res[1]
        norm_w = width / current_res[0]
        norm_h = height / current_res[1]

        # Set crop (picamera expects (x, y, width, height) in normalized coords)
        self.cam.crop = (norm_x, norm_y, norm_w, norm_h)

        # Capture ROI frame
        frame = self.cam.capture_array()

        # Restore original crop
        if self._original_crop:
            self.cam.crop = self._original_crop
        else:
            self.cam.crop = (0.0, 0.0, 1.0, 1.0)  # Full frame

        return frame

    def set_config(self, configs: Dict):
        """
        Update camera configuration

        Based on tested implementation from flow-microscopy-platform
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        self.cam_running_event.clear()

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

        # Update framerate
        if "FrameRate" in configs and configs["FrameRate"]:
            self.config["FrameRate"] = int(configs["FrameRate"])
            self.frame_rate = int(configs["FrameRate"])
            del configs["FrameRate"]
        framerate = self.config.get("FrameRate", 30)
        if isinstance(framerate, (int, float)):
            self.cam.framerate = int(framerate)

        # Update shutter speed
        if "ShutterSpeed" in configs and configs["ShutterSpeed"]:
            self.config["ShutterSpeed"] = int(configs["ShutterSpeed"])
            del configs["ShutterSpeed"]
        shutter = self.config.get("ShutterSpeed", 10000)
        if isinstance(shutter, (int, float)):
            self.cam.shutter_speed = int(shutter)

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
