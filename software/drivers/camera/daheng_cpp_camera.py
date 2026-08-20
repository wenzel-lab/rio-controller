"""
Daheng camera backend using native libdaheng_grabber.so (RIO_DAHENG_CPP=1).

Acquisition thread is C++ (GXDQAllBufs). Python only does ~10 Hz Mono8→JPEG for UI.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from queue import Queue
from threading import Condition, Event, Lock
from typing import Any, Callable, Dict, Generator, Optional, Tuple

import cv2
import numpy as np

from .camera_base import BaseCamera
from .daheng_cpp_grabber import DahengGrabberLib

try:
    from config import CAMERA_DISPLAY_FPS, CAMERA_STREAMING_JPEG_QUALITY
except ImportError:
    CAMERA_STREAMING_JPEG_QUALITY = 75
    CAMERA_DISPLAY_FPS = 10

# GxViewer paints acquisition frames much faster than Rio's default web Disp=10.
# Use a higher UI rate on this host path only (does not change Acq drain).
_CPP_DISPLAY_FPS = float(os.getenv("RIO_DAHENG_CPP_DISPLAY_FPS", "30"))

logger = logging.getLogger(__name__)


def _cpp_enabled() -> bool:
    return os.getenv("RIO_DAHENG_CPP", "").strip().lower() in ("1", "true", "yes", "on")


class DahengCppCamera(BaseCamera):
    """Native-drain Daheng camera for Acq.FPS comparison vs gxipy path."""

    def __init__(self, device_index: int = 0):
        super().__init__()
        self._serial_number = os.getenv("RIO_DAHENG_SN")
        self._grabber = DahengGrabberLib()
        self.cam_running_event: Event = Event()
        self.capture_flag: Event = Event()
        self.capture_queue: Queue[bytes] = Queue(1)
        self._roi_lock = Lock()
        self._pending_hardware_roi: Optional[Tuple[int, int, int, int]] = None
        self._pending_roi_absolute: bool = False
        self._pending_reset_resolution: Optional[Tuple[int, int]] = None
        self._pending_exposure_us: Optional[float] = None
        self._on_roi_applied: Optional[Callable[[bool, str], None]] = None
        self._latest_lock = Lock()
        self._latest_cond = Condition(self._latest_lock)
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_seq: int = 0
        self._display_frame_times: deque[float] = deque(maxlen=4000)
        self._mono_seq: int = 0
        self._want_latest_raw: Event = Event()
        self._record_active: Event = Event()

        self._grabber.open(self._serial_number)
        w, h = self._grabber.stream_size()
        self.config["Width"] = w
        self.config["Height"] = h
        try:
            self.config["ShutterSpeed"] = int(self._grabber.get_exposure_us())
        except Exception:
            self.config["ShutterSpeed"] = 10000
        logger.warning(
            "DahengCppCamera active (RIO_DAHENG_CPP): GxViewer-style open "
            "(UserSet Default load, TriggerMode off, GXDQAllBufs); "
            "exposure=%s us",
            self.config.get("ShutterSpeed"),
        )

    def set_roi_applied_callback(self, callback: Optional[Callable[[bool, str], None]]) -> None:
        self._on_roi_applied = callback

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self.cam_running_event.clear()
        try:
            self._grabber.stop()
        except Exception:
            pass

    def close(self) -> None:
        self.stop()
        try:
            self._grabber.close()
        except Exception:
            pass

    def set_config(self, config: Optional[Dict] = None) -> None:
        if not config:
            return
        self.config.update(config)
        if "ShutterSpeed" in config:
            try:
                self._grabber.set_exposure_us(float(config["ShutterSpeed"]))
            except Exception as exc:
                logger.warning("CPP set exposure failed: %s", exc)

    def set_exposure_us(self, exposure_us: float) -> None:
        us = float(exposure_us)
        if self.cam_running_event.is_set():
            self._pending_exposure_us = us
            return
        self._grabber.set_exposure_us(us)
        self.config["ShutterSpeed"] = int(self._grabber.get_exposure_us())

    def apply_pending_exposure_if_any(self) -> None:
        if self._pending_exposure_us is None:
            return
        us = self._pending_exposure_us
        self._pending_exposure_us = None
        try:
            self._grabber.set_exposure_us(us)
            self.config["ShutterSpeed"] = int(self._grabber.get_exposure_us())
        except Exception as exc:
            logger.warning("CPP pending exposure failed: %s", exc)

    def get_max_resolution(self) -> Tuple[int, int]:
        return self._grabber.sensor_size()

    def get_stream_size(self) -> Tuple[int, int]:
        return self._grabber.stream_size()

    def get_sensor_roi(self) -> Tuple[int, int, int, int]:
        w, h = self._grabber.stream_size()
        # Offsets not exposed via thin API yet — report size at (0,0) unless we extend.
        # Prefer reading via set_roi tracking:
        return (
            int(self.config.get("OffsetX", 0)),
            int(self.config.get("OffsetY", 0)),
            w,
            h,
        )

    def get_roi_constraints(self) -> Dict[str, Any]:
        sw, sh = self.get_max_resolution()
        return {
            "Width": {"min": 16, "max": sw, "inc": 2},
            "Height": {"min": 2, "max": sh, "inc": 2},
            "OffsetX": {"min": 0, "max": sw, "inc": 2},
            "OffsetY": {"min": 0, "max": sh, "inc": 2},
        }

    def validate_and_snap_roi(self, roi: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        x, y, w, h = (int(v) for v in roi)
        sw, sh = self.get_max_resolution()
        w = max(16, min(sw, (w // 2) * 2))
        h = max(2, min(sh, (h // 2) * 2))
        x = max(0, min(sw - w, (x // 2) * 2))
        y = max(0, min(sh - h, (y // 2) * 2))
        return x, y, w, h

    def schedule_roi_hardware(
        self, roi: Tuple[int, int, int, int], absolute: bool = False
    ) -> None:
        with self._roi_lock:
            self._pending_reset_resolution = None
            self._pending_hardware_roi = tuple(int(v) for v in roi)  # type: ignore[assignment]
            self._pending_roi_absolute = bool(absolute)

    def schedule_roi_reset(self, width: int, height: int) -> None:
        with self._roi_lock:
            self._pending_hardware_roi = None
            self._pending_reset_resolution = (int(width), int(height))

    def set_roi_hardware(
        self, roi: Tuple[int, int, int, int], absolute: bool = False
    ) -> bool:
        if self.cam_running_event.is_set():
            self.schedule_roi_hardware(roi, absolute=absolute)
            return True
        return self._apply_roi(roi, absolute=absolute)

    def _apply_roi(self, roi: Tuple[int, int, int, int], absolute: bool = True) -> bool:
        try:
            if absolute:
                x, y, w, h = self.validate_and_snap_roi(roi)
            else:
                # treat as view-relative: same as absolute for this thin backend
                x, y, w, h = self.validate_and_snap_roi(roi)
            self._grabber.set_roi(x, y, w, h)
            self.config["OffsetX"] = x
            self.config["OffsetY"] = y
            self.config["Width"] = w
            self.config["Height"] = h
            self._grabber.sync_afr_max()
            return True
        except Exception as exc:
            logger.warning("CPP ROI apply failed: %s", exc)
            return False

    def apply_pending_roi_if_any(self) -> bool:
        with self._roi_lock:
            pending = self._pending_hardware_roi
            absolute = self._pending_roi_absolute
            reset = self._pending_reset_resolution
            self._pending_hardware_roi = None
            self._pending_reset_resolution = None
        if reset is not None:
            ok = self._apply_roi((0, 0, reset[0], reset[1]), absolute=True)
            if self._on_roi_applied:
                self._on_roi_applied(ok, "reset")
            return ok
        if pending is not None:
            ok = self._apply_roi(pending, absolute=absolute)
            if self._on_roi_applied:
                self._on_roi_applied(ok, "crop")
            return ok
        return False

    def get_measured_framerate(self) -> float:
        return self._grabber.acq_fps()

    def get_actual_framerate(self) -> float:
        return self._grabber.sdk_fps()

    def get_display_framerate(self) -> float:
        now = time.monotonic()
        recent = [t for t in self._display_frame_times if t >= now - 1.0]
        if len(recent) < 2:
            return 0.0
        span = recent[-1] - recent[0]
        return (len(recent) - 1) / span if span > 0 else 0.0

    def get_frame_id(self) -> int:
        return self._grabber.frame_id()

    def get_actual_shutter_speed(self) -> int:
        try:
            return int(self._grabber.get_exposure_us())
        except Exception:
            return int(self.config.get("ShutterSpeed", 10000))

    def get_exposure_range(self) -> Dict[str, float]:
        try:
            lo, hi = self._grabber.get_exposure_range()
            return {"min": float(lo), "max": float(hi)}
        except Exception:
            return {"min": 20.0, "max": 1_000_000.0}

    def get_max_framerate(self) -> float:
        return self.get_actual_framerate()

    def get_bandwidth_bps(self) -> float:
        try:
            w, h = self.get_stream_size()
            return float(w) * float(h) * 8.0 * self.get_actual_framerate()
        except Exception:
            return 0.0

    def _store_rgb(self, mono: np.ndarray, seq: Optional[int] = None) -> np.ndarray:
        rgb = cv2.cvtColor(mono, cv2.COLOR_GRAY2RGB)
        with self._latest_cond:
            self._latest_frame = rgb
            if seq is not None:
                self._latest_seq = int(seq)
            else:
                self._latest_seq += 1
            self._latest_cond.notify_all()
        return rgb

    def begin_latest_frame_capture(self) -> None:
        """Ensure acquisition is running; enable C++ record FIFO if available."""
        self._want_latest_raw.set()
        self._record_active.set()
        self._grabber.set_record_mode(True)
        if not self._grabber.is_running():
            self._grabber.start()
            self.cam_running_event.set()

    def end_latest_frame_capture(self) -> None:
        self._want_latest_raw.clear()
        self._record_active.clear()
        self._grabber.set_record_mode(False)

    def wait_frame_array(self, timeout_s: float = 2.0, after_seq: int = 0) -> Tuple[np.ndarray, int]:
        """Wait for a newer Mono8 frame from the C++ grabber (seq > after_seq)."""
        mono, seq, _fid = self._wait_record_mono(timeout_s=timeout_s, after_seq=after_seq, after_frame_id=-1)
        rgb = self._store_rgb(mono, seq=seq)
        return rgb, int(seq)

    def wait_record_frame(
        self,
        timeout_s: float = 2.0,
        after_seq: int = 0,
        after_frame_id: int = -1,
    ) -> Tuple[np.ndarray, int, int, bool]:
        """Return (frame, seq, frame_id, is_mono) for Record ROI."""
        mono, seq, fid = self._wait_record_mono(
            timeout_s=timeout_s, after_seq=after_seq, after_frame_id=after_frame_id
        )
        return mono, int(seq), int(fid), True

    def record_queue_drops(self) -> int:
        return int(self._grabber.record_queue_drops())

    def _wait_record_mono(
        self, timeout_s: float, after_seq: int, after_frame_id: int
    ) -> Tuple[np.ndarray, int, int]:
        deadline = time.monotonic() + max(0.05, float(timeout_s))
        use_queue = self._record_active.is_set() and getattr(self._grabber, "_has_record_queue", False)
        while True:
            if use_queue:
                got = self._grabber.pop_record_mono8()
                if got is not None:
                    mono, fid, seq = got
                    self._mono_seq = int(seq)
                    return mono, int(seq), int(fid)
            else:
                got = self._grabber.get_latest_mono8(int(after_seq))
                if got is not None:
                    mono, fid, seq = got
                    if int(fid) > int(after_frame_id) or int(seq) > int(after_seq):
                        self._mono_seq = int(seq)
                        return mono, int(seq), int(fid)
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for camera frame")
            time.sleep(0.00002 if use_queue else 0.00005)

    def get_frame_array(self) -> np.ndarray:
        if self._grabber.is_running() or self.cam_running_event.is_set():
            frame, _ = self.wait_frame_array(timeout_s=2.0, after_seq=self._mono_seq)
            return frame
        got = self._grabber.get_latest_mono8(0)
        if got is None:
            raise TimeoutError("No frame from CPP grabber")
        mono, _, seq = got
        self._mono_seq = int(seq)
        return self._store_rgb(mono, seq=seq)

    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        frame = self.get_frame_array()
        x, y, w, h = roi
        return frame[y : y + h, x : x + w]

    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        self.set_config(config or {})
        self._grabber.start()
        self.cam_running_event.set()
        jpeg_interval = 1.0 / max(1.0, float(_CPP_DISPLAY_FPS))
        last_jpeg_t = 0.0
        try:
            while self.cam_running_event.is_set():
                if self._record_active.is_set():
                    time.sleep(0.002)
                    continue
                self.apply_pending_roi_if_any()
                self.apply_pending_exposure_if_any()
                if self.frame_callback:
                    self.frame_callback()
                got = self._grabber.get_latest_mono8(self._mono_seq)
                if got is None:
                    time.sleep(0.001)
                    continue
                mono, _fid, seq = got
                self._mono_seq = seq
                now = time.monotonic()
                need = self._want_latest_raw.is_set() or self.capture_flag.is_set()
                if now - last_jpeg_t < jpeg_interval and not need:
                    continue
                rgb = self._store_rgb(mono, seq=seq)
                _, buffer = cv2.imencode(
                    ".jpg",
                    rgb,
                    [cv2.IMWRITE_JPEG_QUALITY, CAMERA_STREAMING_JPEG_QUALITY],
                )
                last_jpeg_t = now
                self._display_frame_times.append(now)
                if self.capture_flag.is_set():
                    self.capture_queue.put(buffer)
                    self.capture_flag.clear()
                yield buffer.tobytes()
        finally:
            self.stop()
