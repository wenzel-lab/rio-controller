"""
Daheng MER2 camera backend (gxipy).

Uses Daheng Galaxy SDK Python bindings (gxipy).
"""

from __future__ import annotations

import logging
import os
from queue import Queue
from threading import Event
from typing import Optional, Dict, Tuple, Generator, Any

import cv2
import numpy as np

from .camera_base import BaseCamera

logger = logging.getLogger(__name__)

try:
    from gxipy import DeviceManager  # type: ignore

    GXIPY_AVAILABLE = True
except ImportError:
    GXIPY_AVAILABLE = False
    DeviceManager = None  # type: ignore

try:
    from config import CAMERA_STREAMING_JPEG_QUALITY
except ImportError:
    CAMERA_STREAMING_JPEG_QUALITY = 75


class DahengCamera(BaseCamera):
    """Daheng MER2 camera implementation using gxipy."""

    def __init__(self, device_index: int = 0):
        super().__init__()
        if not GXIPY_AVAILABLE:
            raise RuntimeError(
                "gxipy not available. Install the Daheng Galaxy SDK Python bindings."
            )

        env_index = os.getenv("RIO_DAHENG_INDEX")
        self._device_index = int(env_index) if env_index is not None else device_index
        self._serial_number = os.getenv("RIO_DAHENG_SN")
        self._device_manager = None
        self._device = None
        self._data_stream = None

        self.cam_running_event: Event = Event()
        self.capture_flag: Event = Event()
        self.capture_queue: Queue[bytes] = Queue(1)

        self._open_device()

    def _open_device(self) -> None:
        self._device_manager = DeviceManager()
        dev_num, _ = self._device_manager.update_device_list()
        if dev_num < 1:
            raise RuntimeError("No Daheng cameras found (device list empty).")
        if self._serial_number:
            self._device = self._device_manager.open_device_by_sn(self._serial_number)
        else:
            # gxipy uses 1-based index
            self._device = self._device_manager.open_device_by_index(self._device_index + 1)
        if not self._device:
            raise RuntimeError("Failed to open Daheng camera.")
        self._data_stream = self._device.data_stream[0]
        try:
            self._device.AcquisitionFrameRate.set(1000)
            self._device.AcquisitionFrameRateMode.set(1)
            self._device.DeviceLinkThroughputLimitMode.set(0)
        except Exception:
            pass

    def start(self) -> None:
        if self._device is None:
            raise RuntimeError("Camera not initialized")

    def stop(self) -> None:
        self.cam_running_event.clear()
        if self._device:
            try:
                self._device.stream_off()
            except Exception:
                pass

    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        if self._device is None or self._data_stream is None:
            raise RuntimeError("Camera not initialized")

        self.set_config(config or {})
        self._device.stream_on()
        self.cam_running_event.set()
        try:
            while self.cam_running_event.is_set():
                if self.frame_callback:
                    self.frame_callback()
                raw_image = self._data_stream.get_image()
                if raw_image is None:
                    continue
                rgb_image = raw_image.convert("RGB") if hasattr(raw_image, "convert") else raw_image
                frame = rgb_image.get_numpy_array()
                if frame is None:
                    continue
                _, buffer = cv2.imencode(
                    ".jpg",
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, CAMERA_STREAMING_JPEG_QUALITY],
                )
                if self.capture_flag.is_set():
                    self.capture_queue.put(buffer)
                    self.capture_flag.clear()
                yield buffer.tobytes()
        finally:
            self.stop()

    def get_frame_array(self) -> np.ndarray:
        if self._device is None or self._data_stream is None:
            raise RuntimeError("Camera not initialized")
        raw_image = self._data_stream.get_image()
        if raw_image is None:
            raise RuntimeError("No image returned from camera")
        rgb_image = raw_image.convert("RGB") if hasattr(raw_image, "convert") else raw_image
        frame = rgb_image.get_numpy_array()
        if frame is None:
            raise RuntimeError("Failed to decode camera frame")
        return frame

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        frame = self.get_frame_array()
        x, y, w, h = roi
        return frame[y : y + h, x : x + w]

    def set_config(self, configs: Dict) -> None:
        if self._device is None:
            return
        if not configs:
            return
        self.config.update(configs)
        try:
            if "Width" in configs:
                self._device.Width.set(int(configs["Width"]))
            if "Height" in configs:
                self._device.Height.set(int(configs["Height"]))
            if "FrameRate" in configs:
                try:
                    self._device.AcquisitionFrameRateMode.set(1)
                except Exception:
                    pass
                self._device.AcquisitionFrameRate.set(float(configs["FrameRate"]))
            if "ShutterSpeed" in configs:
                self._device.ExposureTime.set(float(configs["ShutterSpeed"]))
        except Exception as exc:
            logger.warning("Failed to apply Daheng config: %s", exc)

    def set_roi_hardware(self, roi: Tuple[int, int, int, int]) -> bool:
        if self._device is None:
            return False
        x, y, w, h = roi
        try:
            self._device.OffsetX.set(int(x))
            self._device.OffsetY.set(int(y))
            self._device.Width.set(int(w))
            self._device.Height.set(int(h))
            return True
        except Exception as exc:
            logger.warning("Failed to set Daheng hardware ROI: %s", exc)
            return False

    def get_actual_framerate(self) -> float:
        if self._device is None:
            return float(self.config.get("FrameRate", 30))
        try:
            return float(self._device.CurrentAcquisitionFrameRate.get())
        except Exception:
            return float(self.config.get("FrameRate", 30))

    def get_actual_shutter_speed(self) -> int:
        if self._device is None:
            return int(self.config.get("ShutterSpeed", 10000))
        try:
            return int(self._device.ExposureTime.get())
        except Exception:
            return int(self.config.get("ShutterSpeed", 10000))
