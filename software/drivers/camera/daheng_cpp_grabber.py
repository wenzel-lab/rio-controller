"""
ctypes loader for libdaheng_grabber.so (RIO_DAHENG_CPP=1).
"""

from __future__ import annotations

import ctypes
import os
from ctypes import (
    POINTER,
    c_char_p,
    c_double,
    c_int,
    c_int32,
    c_uint64,
    c_uint8,
)
from pathlib import Path
from typing import Optional, Tuple


def _default_lib_paths() -> list[Path]:
    here = Path(__file__).resolve()
    # software/drivers/camera -> software/native/daheng_grabber
    native = here.parents[2] / "native" / "daheng_grabber" / "libdaheng_grabber.so"
    env = os.getenv("RIO_DAHENG_GRABBER_LIB")
    paths = []
    if env:
        paths.append(Path(env))
    paths.append(native)
    paths.append(Path("libdaheng_grabber.so"))
    return paths


class DahengGrabberLib:
    def __init__(self, lib_path: Optional[str] = None):
        path = None
        if lib_path:
            path = Path(lib_path)
        else:
            for p in _default_lib_paths():
                if p.is_file():
                    path = p
                    break
        if path is None or not path.is_file():
            raise FileNotFoundError(
                "libdaheng_grabber.so not found. Build software/native/daheng_grabber "
                "or set RIO_DAHENG_GRABBER_LIB."
            )
        self._lib = ctypes.CDLL(str(path))
        self._bind()

    def _bind(self) -> None:
        L = self._lib
        L.daheng_grabber_open.argtypes = [c_char_p]
        L.daheng_grabber_open.restype = c_int
        L.daheng_grabber_close.argtypes = []
        L.daheng_grabber_close.restype = None
        L.daheng_grabber_get_sensor_size.argtypes = [POINTER(c_int32), POINTER(c_int32)]
        L.daheng_grabber_get_sensor_size.restype = c_int
        L.daheng_grabber_get_stream_size.argtypes = [POINTER(c_int32), POINTER(c_int32)]
        L.daheng_grabber_get_stream_size.restype = c_int
        L.daheng_grabber_set_roi.argtypes = [c_int32, c_int32, c_int32, c_int32]
        L.daheng_grabber_set_roi.restype = c_int
        L.daheng_grabber_set_exposure_us.argtypes = [c_double]
        L.daheng_grabber_set_exposure_us.restype = c_int
        L.daheng_grabber_get_exposure_us.argtypes = [POINTER(c_double)]
        L.daheng_grabber_get_exposure_us.restype = c_int
        L.daheng_grabber_sync_afr_max.argtypes = []
        L.daheng_grabber_sync_afr_max.restype = c_int
        L.daheng_grabber_start.argtypes = []
        L.daheng_grabber_start.restype = c_int
        L.daheng_grabber_stop.argtypes = []
        L.daheng_grabber_stop.restype = None
        L.daheng_grabber_is_running.argtypes = []
        L.daheng_grabber_is_running.restype = c_int
        L.daheng_grabber_get_latest_mono8.argtypes = [
            POINTER(c_uint8),
            c_int32,
            POINTER(c_int32),
            POINTER(c_int32),
            POINTER(c_uint64),
            POINTER(c_uint64),
            c_uint64,
        ]
        L.daheng_grabber_get_latest_mono8.restype = c_int
        L.daheng_grabber_get_acq_fps.argtypes = []
        L.daheng_grabber_get_acq_fps.restype = c_double
        L.daheng_grabber_get_sdk_fps.argtypes = []
        L.daheng_grabber_get_sdk_fps.restype = c_double
        L.daheng_grabber_get_frame_id.argtypes = []
        L.daheng_grabber_get_frame_id.restype = c_uint64

    def open(self, serial: Optional[str]) -> None:
        sn = serial.encode("utf-8") if serial else None
        if self._lib.daheng_grabber_open(sn) != 0:
            raise RuntimeError("daheng_grabber_open failed")

    def close(self) -> None:
        self._lib.daheng_grabber_close()

    def sensor_size(self) -> Tuple[int, int]:
        w = c_int32()
        h = c_int32()
        if self._lib.daheng_grabber_get_sensor_size(ctypes.byref(w), ctypes.byref(h)) != 0:
            raise RuntimeError("get_sensor_size failed")
        return int(w.value), int(h.value)

    def stream_size(self) -> Tuple[int, int]:
        w = c_int32()
        h = c_int32()
        if self._lib.daheng_grabber_get_stream_size(ctypes.byref(w), ctypes.byref(h)) != 0:
            raise RuntimeError("get_stream_size failed")
        return int(w.value), int(h.value)

    def set_roi(self, ox: int, oy: int, w: int, h: int) -> None:
        if self._lib.daheng_grabber_set_roi(ox, oy, w, h) != 0:
            raise RuntimeError("set_roi failed")

    def set_exposure_us(self, us: float) -> None:
        if self._lib.daheng_grabber_set_exposure_us(float(us)) != 0:
            raise RuntimeError("set_exposure_us failed")

    def get_exposure_us(self) -> float:
        v = c_double()
        if self._lib.daheng_grabber_get_exposure_us(ctypes.byref(v)) != 0:
            raise RuntimeError("get_exposure_us failed")
        return float(v.value)

    def sync_afr_max(self) -> None:
        self._lib.daheng_grabber_sync_afr_max()

    def start(self) -> None:
        if self._lib.daheng_grabber_start() != 0:
            raise RuntimeError("daheng_grabber_start failed")

    def stop(self) -> None:
        self._lib.daheng_grabber_stop()

    def is_running(self) -> bool:
        return self._lib.daheng_grabber_is_running() != 0

    def get_latest_mono8(self, after_seq: int = 0):
        import numpy as np

        # Allocate for max sensor; resize after size known via probe capacity.
        # Use stream size hint.
        try:
            sw, sh = self.stream_size()
        except Exception:
            sw, sh = 1440, 1080
        capacity = max(sw * sh, 1440 * 1080)
        buf = (c_uint8 * capacity)()
        w = c_int32()
        h = c_int32()
        fid = c_uint64()
        seq = c_uint64()
        rc = self._lib.daheng_grabber_get_latest_mono8(
            buf,
            capacity,
            ctypes.byref(w),
            ctypes.byref(h),
            ctypes.byref(fid),
            ctypes.byref(seq),
            c_uint64(after_seq),
        )
        if rc == 0:
            return None
        if rc < 0:
            raise RuntimeError("get_latest_mono8 failed")
        arr = np.ctypeslib.as_array(buf)[: int(w.value) * int(h.value)].copy()
        arr = arr.reshape((int(h.value), int(w.value)))
        return arr, int(fid.value), int(seq.value)

    def acq_fps(self) -> float:
        return float(self._lib.daheng_grabber_get_acq_fps())

    def sdk_fps(self) -> float:
        return float(self._lib.daheng_grabber_get_sdk_fps())

    def frame_id(self) -> int:
        return int(self._lib.daheng_grabber_get_frame_id())
