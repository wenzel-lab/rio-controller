"""
PiCamera V2 Implementation (64-bit)
Based on tested PiCamera code from flow-microscopy-platform

Uses picamera2 library for 64-bit Raspberry Pi OS
"""

from picamera2 import Picamera2
import cv2
import os
import time
from typing import Optional, Dict, Tuple, Generator, Any
import numpy as np
from queue import Queue
from threading import Event

from .camera_base import BaseCamera


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
        self.cam: Optional[Picamera2] = None
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            try:
                self.cam = Picamera2()
            except Exception as e:
                print(f"Failed to initialize Picamera2: {e}")
                self.cam = None

        # Default configuration (from tested code)
        self.config = {
            "size": [640, 480],
            "ExposureTime": 10000,
            "FrameRate": 30,
        }
        self.frame_rate = 30

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
            self.cam.configure(
                self.cam.create_video_configuration(main={"size": size_tuple})
            )
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
        self.cam.configure(
            self.cam.create_video_configuration(main={"size": size_tuple})
        )
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

            # Encode as JPEG
            ret, buffer = cv2.imencode(".jpg", frame)

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

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI frame using software cropping

        Args:
            roi: (x, y, width, height) tuple

        Returns:
            numpy.ndarray: ROI frame as RGB numpy array

        Note: picamera2 doesn't support hardware ROI like picamera,
        so we crop the numpy array in software (still fast)
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")

        if not self.cam.started:
            self.start()

        x, y, width, height = roi

        # Capture full frame (from tested code)
        frame = self.cam.capture_array()
        # picamera2 returns BGR, convert to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Crop ROI: frame[y:y+h, x:x+w]
        roi_frame = frame[y : y + height, x : x + width]

        return roi_frame

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
        self.cam.configure(
            self.cam.create_video_configuration(main={"size": size_tuple})
        )
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
                "value": int(self.config.get("size", [640, 480])[1]) if isinstance(self.config.get("size", []), (list, tuple)) and len(self.config.get("size", [])) > 1 else 480,
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
                "value": int(self.config.get("size", [640, 480])[0]) if isinstance(self.config.get("size", []), (list, tuple)) and len(self.config.get("size", [])) > 0 else 640,
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
