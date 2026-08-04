"""
Daheng MER2 camera backend (gxipy).

Uses Daheng Galaxy SDK Python bindings (gxipy).
"""

from __future__ import annotations

import logging
import math
import os
import time
from collections import deque
from contextlib import contextmanager
from queue import Queue
from threading import Event, Lock
from typing import Any, Callable, Dict, Generator, Optional, Tuple

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
    from config import CAMERA_DISPLAY_FPS, CAMERA_STREAMING_JPEG_QUALITY
except ImportError:
    CAMERA_STREAMING_JPEG_QUALITY = 75
    CAMERA_DISPLAY_FPS = 10


def _snap_to_increment(value: int, min_val: int, max_val: int, increment: int) -> int:
    """Galaxy Roi.cpp: value = (value / inc) * inc, then clamp to [min, max]."""
    inc = max(1, int(increment))
    snapped = (int(value) // inc) * inc
    return max(min_val, min(max_val, snapped))


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
        self._frame_times: deque[float] = deque(maxlen=240)
        self._last_frame_id: int = 0
        self._roi_lock = Lock()
        self._pending_hardware_roi: Optional[Tuple[int, int, int, int]] = None
        self._pending_roi_absolute: bool = False
        self._pending_reset_resolution: Optional[Tuple[int, int]] = None
        self._pending_exposure_us: Optional[float] = None
        self._on_roi_applied: Optional[Callable[[bool, str], None]] = None

        self._open_device()

    def set_roi_applied_callback(self, callback: Optional[Callable[[bool, str], None]]) -> None:
        """Optional callback(ok, kind) where kind is 'crop' or 'reset'."""
        self._on_roi_applied = callback

    def _open_device(self) -> None:
        self._device_manager = DeviceManager()
        dev_num, _ = self._device_manager.update_device_list()
        if dev_num < 1:
            raise RuntimeError("No Daheng cameras found (device list empty).")
        if self._serial_number:
            self._device = self._device_manager.open_device_by_sn(self._serial_number)
        else:
            self._device = self._device_manager.open_device_by_index(self._device_index + 1)
        if not self._device:
            raise RuntimeError("Failed to open Daheng camera.")
        self._data_stream = self._device.data_stream[0]
        try:
            self._device.DeviceLinkThroughputLimitMode.set(0)
        except Exception:
            pass
        self._reset_full_sensor()
        # Prefer device max FPS (not Pi CAMERA_DEFAULT_FPS=30). ROI changes re-sync.
        # Exposure is restored inside sync — raising AFR alone clamps ExposureTime to ~100us (black).
        self._sync_acquisition_framerate_to_max()
        self._ensure_default_exposure()

    def cancel_pending_roi(self) -> None:
        with self._roi_lock:
            self._pending_hardware_roi = None
            self._pending_reset_resolution = None

    def schedule_roi_reset(self, width: int, height: int) -> None:
        """Queue ROI reset for capture thread (Galaxy: never change ROI off capture thread)."""
        with self._roi_lock:
            self._pending_hardware_roi = None
            self._pending_reset_resolution = (int(width), int(height))

    def get_sensor_roi(self) -> Tuple[int, int, int, int]:
        """Current absolute sensor ROI (OffsetX, OffsetY, Width, Height)."""
        if self._device is None:
            w = int(self.config.get("Width", 640))
            h = int(self.config.get("Height", 480))
            return (0, 0, w, h)
        try:
            return (
                int(self._device.OffsetX.get()),
                int(self._device.OffsetY.get()),
                int(self._device.Width.get()),
                int(self._device.Height.get()),
            )
        except Exception:
            return (0, 0, *self.get_stream_size())

    def _reset_full_sensor(self) -> None:
        """Restore full sensor ROI — Galaxy Roi.cpp one-feature-at-a-time pattern."""
        if self._device is None:
            return
        max_w, max_h = self.get_max_resolution()
        self.reset_to_resolution(max_w, max_h)

    def reset_to_resolution(self, width: int, height: int) -> None:
        """
        Set ROI to (0,0,width,height) using Galaxy SDK pattern.

        While acquisition is running, changes are queued for the capture thread
        (GxViewer disables ROI UI during acquisition; stream_off/on must not race get_image).
        """
        if self._device is None:
            return
        if self.cam_running_event.is_set():
            self.schedule_roi_reset(width, height)
            return
        self._do_reset_to_resolution(width, height)

    def _do_reset_to_resolution(self, width: int, height: int) -> bool:
        if self._device is None:
            return False
        ok = False
        with self._roi_lock:
            was_on = self.cam_running_event.is_set()
            if was_on:
                try:
                    self._device.stream_off()
                except Exception as exc:
                    logger.warning("stream_off before ROI reset failed: %s", exc)
            try:
                max_w, max_h = self.get_max_resolution()
                self._set_genicam_int(self._device.OffsetX, 0)
                self._set_genicam_int(self._device.OffsetY, 0)
                self._set_genicam_int(self._device.Width, max_w)
                self._set_genicam_int(self._device.Height, max_h)
                w = self._set_genicam_int(self._device.Width, int(width))
                h = self._set_genicam_int(self._device.Height, int(height))
                self.config["Width"] = w
                self.config["Height"] = h
                self._sync_acquisition_framerate_to_max()
                logger.info("Daheng ROI reset: OffsetX=0 OffsetY=0 Width=%s Height=%s", w, h)
                ok = True
            except Exception as exc:
                logger.warning("Failed to reset Daheng ROI: %s", exc)
            finally:
                if was_on:
                    try:
                        self._device.stream_on()
                    except Exception as exc:
                        logger.warning("stream_on after ROI reset failed: %s", exc)
        return ok

    def _ensure_default_exposure(self) -> None:
        """ExposureAuto off + sane ExposureTime if device was left at an extreme."""
        if self._device is None:
            return
        try:
            self._device.ExposureAuto.set(0)
            current = float(self._device.ExposureTime.get())
            # AFR→max clamps ExposureTime to ~100us; treat <1ms as unusable for live view.
            if current > 500_000 or current < 1_000:
                rng = self._device.ExposureTime.get_range()
                target = max(float(rng["min"]), min(float(rng["max"]), 50_000.0))
                self._device.ExposureTime.set(target)
                self.config["ShutterSpeed"] = int(self._device.ExposureTime.get())
            else:
                self.config["ShutterSpeed"] = int(current)
        except Exception as exc:
            logger.warning("Failed to set default Daheng exposure: %s", exc)

    def _sync_acquisition_framerate_to_max(self, *, preserve_exposure: bool = True) -> None:
        """
        Raise AcquisitionFrameRate to the current GenICam range max.

        MER2 max FPS rises when hardware ROI shrinks (and falls when ROI expands).
        GenICam keeps the prior setpoint (often Rio's Pi default of 30), so we must
        re-apply after every ROI change — otherwise acq_fps stays stuck at 30.

        Setting AFR near absolute max can clamp ExposureTime to ~frame period.
        When preserve_exposure=True (open / ROI reset), restore a usable pre-sync
        exposure so the live feed is not crushed to ~100us. When False (ROI crop
        for high-speed), leave exposure alone — caller may unlock FPS separately.
        """
        if self._device is None:
            return
        try:
            preserved_exp = None
            try:
                preserved_exp = float(self._device.ExposureTime.get())
            except Exception:
                pass
            try:
                self._device.AcquisitionFrameRateMode.set(1)
            except Exception:
                pass
            rng = self._device.AcquisitionFrameRate.get_range()
            max_fps = float(rng["max"])
            self._device.AcquisitionFrameRate.set(max_fps)

            if preserve_exposure:
                try:
                    post_exp = float(self._device.ExposureTime.get())
                    if (
                        preserved_exp is not None
                        and preserved_exp >= 1_000.0
                        and post_exp < preserved_exp * 0.5
                    ):
                        self._device.ExposureAuto.set(0)
                        er = self._device.ExposureTime.get_range()
                        target = max(float(er["min"]), min(float(er["max"]), preserved_exp))
                        self._device.ExposureTime.set(target)
                        self.config["ShutterSpeed"] = int(self._device.ExposureTime.get())
                    else:
                        self.config["ShutterSpeed"] = int(post_exp)
                except Exception as exc:
                    logger.debug("Exposure restore after AFR sync failed: %s", exc)
            else:
                try:
                    self.config["ShutterSpeed"] = int(self._device.ExposureTime.get())
                except Exception:
                    pass

            actual = float(self._device.AcquisitionFrameRate.get())
            self.config["FrameRate"] = actual
            logger.info(
                "Daheng AcquisitionFrameRate → %.2f (range max=%.2f, exposure=%sus)",
                actual,
                max_fps,
                self.config.get("ShutterSpeed", "?"),
            )
        except Exception as exc:
            logger.debug("AcquisitionFrameRate sync to max failed: %s", exc)

    def _unlock_exposure_for_high_fps(self, target_fps: float = 1000.0) -> None:
        """
        Cap ExposureTime so CurrentAcquisitionFrameRate can climb after ROI shrink.

        Acq FPS is min(AFR setpoint, ~1e6/ExposureTime, ROI/bandwidth limits).
        Long preview exposures (e.g. 15ms → ~66 FPS) hide the ROI speedup unless
        exposure is shortened. UI exposure control can raise it again for brightness.
        """
        if self._device is None:
            return
        try:
            self._device.ExposureAuto.set(0)
            try:
                max_fps = float(self._device.AcquisitionFrameRate.get_range()["max"])
            except Exception:
                max_fps = target_fps
            goal_fps = max(1.0, min(float(target_fps), max_fps if max_fps > 0 else target_fps))
            # Leave ~5% headroom so exposure is not the sole limiter at goal_fps.
            max_exp_us = max(100.0, 0.95e6 / goal_fps)
            er = self._device.ExposureTime.get_range()
            max_exp_us = max(float(er["min"]), min(float(er["max"]), max_exp_us))
            current = float(self._device.ExposureTime.get())
            if current <= max_exp_us + 1.0:
                self.config["ShutterSpeed"] = int(current)
                return
            # Brightness compensation (approx): Gain_dB += 20*log10(exp_ratio)
            try:
                ratio = current / max_exp_us
                boost_db = 20.0 * math.log10(ratio) if ratio > 1.0 else 0.0
                gain = float(self._device.Gain.get())
                gr = self._device.Gain.get_range()
                new_gain = min(float(gr["max"]), gain + boost_db)
                if new_gain > gain + 0.1:
                    self._device.Gain.set(new_gain)
                    logger.info(
                        "Daheng Gain %.1f → %.1f dB (compensate exposure %.0f→%.0f us)",
                        gain,
                        new_gain,
                        current,
                        max_exp_us,
                    )
            except Exception as exc:
                logger.debug("Gain compensate after exposure unlock failed: %s", exc)

            self._device.ExposureTime.set(max_exp_us)
            self.config["ShutterSpeed"] = int(self._device.ExposureTime.get())
            # Re-assert AFR max after exposure change (coupled GenICam limits).
            try:
                self._device.AcquisitionFrameRateMode.set(1)
                afr_max = float(self._device.AcquisitionFrameRate.get_range()["max"])
                self._device.AcquisitionFrameRate.set(afr_max)
                self.config["FrameRate"] = float(self._device.AcquisitionFrameRate.get())
            except Exception:
                pass
            logger.info(
                "Daheng exposure unlocked for high FPS: %.0f → %s us (target ≥%.0f FPS)",
                current,
                self.config["ShutterSpeed"],
                goal_fps,
            )
        except Exception as exc:
            logger.debug("Exposure unlock for high FPS failed: %s", exc)

    @contextmanager
    def _stream_paused(self):
        was_on = self.cam_running_event.is_set()
        if was_on and self._device:
            try:
                self._device.stream_off()
            except Exception as exc:
                logger.warning("stream_off failed: %s", exc)
        try:
            yield
        finally:
            if was_on and self._device:
                try:
                    self._device.stream_on()
                except Exception as exc:
                    logger.warning("stream_on failed: %s", exc)

    def _int_constraint(self, feature, fallback: Dict[str, int]) -> Dict[str, int]:
        out = dict(fallback)
        if self._device is None or feature is None:
            return out
        try:
            if not feature.is_implemented():
                return out
            rng = feature.get_range()
            out["min"] = int(rng["min"])
            out["max"] = int(rng["max"])
            out["increment"] = int(rng.get("inc", 1))
            out["current"] = int(feature.get())
        except Exception:
            pass
        return out

    def _set_genicam_int(self, feature, value: int) -> int:
        """
        Set one GenICam integer feature — Galaxy Roi.cpp slider handler pattern.

        Snap to increment, GXSetIntValue, then refresh ranges via get_range().
        """
        if self._device is None or feature is None:
            return int(value)
        c = self._int_constraint(feature, {"min": 0, "max": value, "increment": 1})
        snapped = _snap_to_increment(value, c["min"], c["max"], c["increment"])
        feature.set(snapped)
        return int(feature.get())

    def _apply_roi_absolute(self, offset_x: int, offset_y: int, width: int, height: int) -> bool:
        """
        Apply absolute sensor ROI (OffsetX, OffsetY, Width, Height).

        Galaxy GxViewer + Roi.cpp:
        - stream_off before ROI changes (ROI UI disabled while acquiring)
        - expand to full sensor (Offset 0, max W/H) to avoid coupled-limit dead ends
        - one GXSetIntValue per feature; snap via _set_genicam_int; device refreshes ranges
        - final set order: Width, Height, OffsetX, OffsetY (Rio batch; SDK uses one-at-a-time UI)
        """
        if self._device is None:
            return False
        if self.is_multi_roi_enabled():
            logger.warning("MultiROI mode enabled — single ROI not supported (GxViewer.cpp)")
            return False
        with self._roi_lock:
            was_on = self.cam_running_event.is_set()
            if was_on:
                try:
                    self._device.stream_off()
                except Exception as exc:
                    logger.warning("stream_off before ROI failed: %s", exc)
            try:
                max_w, max_h = self.get_max_resolution()
                self._set_genicam_int(self._device.OffsetX, 0)
                self._set_genicam_int(self._device.OffsetY, 0)
                self._set_genicam_int(self._device.Width, max_w)
                self._set_genicam_int(self._device.Height, max_h)
                aw = self._set_genicam_int(self._device.Width, width)
                ah = self._set_genicam_int(self._device.Height, height)
                ax = self._set_genicam_int(self._device.OffsetX, offset_x)
                ay = self._set_genicam_int(self._device.OffsetY, offset_y)
                ax = int(self._device.OffsetX.get())
                ay = int(self._device.OffsetY.get())
                aw = int(self._device.Width.get())
                ah = int(self._device.Height.get())
                self.config["Width"] = aw
                self.config["Height"] = ah
                # ROI crop: raise AFR and shorten exposure so acq_fps can climb
                # (long preview exposures e.g. 15ms otherwise cap CurrentAcq at ~66).
                self._sync_acquisition_framerate_to_max(preserve_exposure=False)
                self._unlock_exposure_for_high_fps(target_fps=1000.0)
                logger.info("Daheng ROI: OffsetX=%s OffsetY=%s Width=%s Height=%s", ax, ay, aw, ah)
                return True
            except Exception as exc:
                logger.warning("Failed to set Daheng hardware ROI: %s", exc)
                return False
            finally:
                if was_on:
                    try:
                        self._device.stream_on()
                    except Exception as exc:
                        logger.warning("stream_on after ROI failed: %s", exc)

    def _note_frame(self) -> None:
        self._frame_times.append(time.monotonic())

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
        # Drain acquisition at full rate, but JPEG only at display FPS so high
        # AFR (after ROI / short exposure) does not stall the UI pipeline.
        jpeg_interval = 1.0 / max(1.0, float(CAMERA_DISPLAY_FPS))
        last_jpeg_t = 0.0
        try:
            while self.cam_running_event.is_set():
                self.apply_pending_roi_if_any()
                self.apply_pending_exposure_if_any()
                if self.frame_callback:
                    self.frame_callback()
                try:
                    raw_image = self._data_stream.get_image(timeout=1000)
                except TypeError:
                    raw_image = self._data_stream.get_image()
                except Exception:
                    continue
                if raw_image is None:
                    continue
                try:
                    self._last_frame_id = int(raw_image.get_frame_id())
                except Exception:
                    self._last_frame_id += 1
                self._note_frame()
                now = time.monotonic()
                if now - last_jpeg_t < jpeg_interval and not self.capture_flag.is_set():
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
                last_jpeg_t = now
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
        fh, fw = frame.shape[:2]
        if abs(fw - w) <= 4 and abs(fh - h) <= 4:
            return frame
        return frame[y : y + h, x : x + w]

    def set_config(self, configs: Dict) -> None:
        if self._device is None or not configs:
            return
        self.config.update(configs)
        if "ShutterSpeed" in configs:
            self.set_exposure_us(float(configs["ShutterSpeed"]))
            configs = {k: v for k, v in configs.items() if k != "ShutterSpeed"}
        if not configs:
            return
        if self.cam_running_event.is_set() and ("Width" in configs or "Height" in configs):
            logger.debug("Defer Width/Height config while acquisition is active")
            return
        try:
            if "Width" in configs:
                w = self._set_genicam_int(self._device.Width, int(configs["Width"]))
                self.config["Width"] = w
            if "Height" in configs:
                h = self._set_genicam_int(self._device.Height, int(configs["Height"]))
                self.config["Height"] = h
            if "FrameRate" in configs:
                # Explicit setpoint (e.g. strobe timing). Clamp to live device max.
                try:
                    self._device.AcquisitionFrameRateMode.set(1)
                except Exception:
                    pass
                requested = float(configs["FrameRate"])
                try:
                    max_fps = float(self._device.AcquisitionFrameRate.get_range()["max"])
                    requested = min(requested, max_fps)
                except Exception:
                    pass
                self._device.AcquisitionFrameRate.set(requested)
                self.config["FrameRate"] = float(self._device.AcquisitionFrameRate.get())
        except Exception as exc:
            logger.warning("Failed to apply Daheng config: %s", exc)

    def set_exposure_us(self, exposure_us: float) -> None:
        """Galaxy ExposureGain.cpp: ExposureAuto off, then GXSetFloatValue(ExposureTime)."""
        if self._device is None:
            return
        if self.cam_running_event.is_set():
            with self._roi_lock:
                self._pending_exposure_us = float(exposure_us)
            return
        self._apply_exposure_us(float(exposure_us))

    def _apply_exposure_us(self, exposure_us: float) -> None:
        if self._device is None:
            return
        try:
            self._device.ExposureAuto.set(0)
            rng = self._device.ExposureTime.get_range()
            exposure_us = max(float(rng["min"]), min(float(rng["max"]), float(exposure_us)))
            self._device.ExposureTime.set(exposure_us)
            self.config["ShutterSpeed"] = int(self._device.ExposureTime.get())
        except Exception as exc:
            logger.warning("Failed to set Daheng exposure: %s", exc)

    def apply_pending_exposure_if_any(self) -> bool:
        with self._roi_lock:
            pending = self._pending_exposure_us
            self._pending_exposure_us = None
        if pending is None:
            return False
        self._apply_exposure_us(pending)
        return True

    def get_exposure_range(self) -> Dict[str, float]:
        if self._device is None:
            return {"min": 100.0, "max": 1_000_000.0}
        try:
            rng = self._device.ExposureTime.get_range()
            return {"min": float(rng["min"]), "max": float(rng["max"])}
        except Exception:
            return {"min": 100.0, "max": 1_000_000.0}

    def get_max_resolution(self) -> Tuple[int, int]:
        if self._device is None:
            size = self.config.get("size", [640, 480])
            return int(size[0]), int(size[1])
        try:
            return int(self._device.WidthMax.get()), int(self._device.HeightMax.get())
        except Exception:
            return (640, 480)

    def get_roi_constraints(self) -> Dict[str, Any]:
        max_w, max_h = self.get_max_resolution()
        sw, sh = self.get_stream_size()
        constraints = {
            "offset_x": {"min": 0, "max": max_w, "increment": 2, "current": 0},
            "offset_y": {"min": 0, "max": max_h, "increment": 2, "current": 0},
            "width": {"min": 8, "max": max_w, "increment": 4, "current": sw},
            "height": {"min": 8, "max": max_h, "increment": 4, "current": sh},
            "sensor_width": max_w,
            "sensor_height": max_h,
            "stream_width": sw,
            "stream_height": sh,
        }
        if self._device is None:
            return constraints
        constraints["offset_x"] = self._int_constraint(self._device.OffsetX, constraints["offset_x"])
        constraints["offset_y"] = self._int_constraint(self._device.OffsetY, constraints["offset_y"])
        constraints["width"] = self._int_constraint(self._device.Width, constraints["width"])
        constraints["height"] = self._int_constraint(self._device.Height, constraints["height"])
        constraints["stream_width"] = int(constraints["width"]["current"])
        constraints["stream_height"] = int(constraints["height"]["current"])
        return constraints

    def is_multi_roi_enabled(self) -> bool:
        """GxViewer.cpp CheckMultiROIOn — Rio does not support MultiROI mode."""
        if self._device is None:
            return False
        try:
            mode = self._device.RegionSendMode.get()
            return int(mode) == 1
        except Exception:
            return False

    def snap_view_roi(self, roi: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """View-relative ROI → absolute snap → view coords (matches post-expand W,H,Ox,Oy apply)."""
        if self._device is None:
            return roi
        try:
            cur_ox = int(self._device.OffsetX.get())
            cur_oy = int(self._device.OffsetY.get())
        except Exception:
            cur_ox, cur_oy = 0, 0
        vx, vy, vw, vh = roi
        ax, ay, aw, ah = self.validate_and_snap_roi((cur_ox + vx, cur_oy + vy, vw, vh))
        return (ax - cur_ox, ay - cur_oy, aw, ah)

    def validate_and_snap_roi(self, roi: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """
        Snap absolute sensor ROI (OffsetX, OffsetY, Width, Height).

        Galaxy Roi.cpp: floor to increment `(value / inc) * inc`, clamp to live min/max.
        Atomic apply order in _apply_roi_absolute (after expand): Width → Height → OffsetX → OffsetY.
        Pre-snap uses the same W/H-before-offset order with coupled sensor bounds.
        """
        x, y, width, height = roi
        max_w, max_h = self.get_max_resolution()
        c = self.get_roi_constraints()
        min_w = int(c["width"]["min"])
        min_h = int(c["height"]["min"])
        w_inc = int(c["width"]["increment"])
        h_inc = int(c["height"]["increment"])
        ox_inc = int(c["offset_x"]["increment"])
        oy_inc = int(c["offset_y"]["increment"])

        width = _snap_to_increment(width, min_w, max_w, w_inc)
        height = _snap_to_increment(height, min_h, max_h, h_inc)
        x = _snap_to_increment(x, 0, max(0, max_w - width), ox_inc)
        y = _snap_to_increment(y, 0, max(0, max_h - height), oy_inc)
        if x + width > max_w:
            width = _snap_to_increment(max_w - x, min_w, max_w, w_inc)
        if y + height > max_h:
            height = _snap_to_increment(max_h - y, min_h, max_h, h_inc)
        if x > max_w - width:
            x = _snap_to_increment(max(0, max_w - width), 0, max(0, max_w - width), ox_inc)
        if y > max_h - height:
            y = _snap_to_increment(max(0, max_h - height), 0, max(0, max_h - height), oy_inc)
        return (x, y, width, height)

    def get_stream_size(self) -> Tuple[int, int]:
        if self._device is None:
            size = self.config.get("size", [640, 480])
            return int(size[0]), int(size[1])
        try:
            return int(self._device.Width.get()), int(self._device.Height.get())
        except Exception:
            return int(self.config.get("Width", 640)), int(self.config.get("Height", 480))

    def _apply_roi_genicam(self, roi: Tuple[int, int, int, int]) -> bool:
        """View-relative (x,y,w,h) → absolute sensor coords → Galaxy Roi.cpp apply."""
        if self._device is None:
            return False
        try:
            cur_ox = int(self._device.OffsetX.get())
            cur_oy = int(self._device.OffsetY.get())
        except Exception:
            cur_ox, cur_oy = 0, 0
        vx, vy, vw, vh = roi
        abs_roi = self.validate_and_snap_roi((cur_ox + vx, cur_oy + vy, vw, vh))
        return self._apply_roi_absolute(*abs_roi)

    def _apply_roi_abs_snapped(self, roi: Tuple[int, int, int, int]) -> bool:
        """Absolute sensor coords (OffsetX, OffsetY, W, H) → snap → apply."""
        if self._device is None:
            return False
        abs_roi = self.validate_and_snap_roi(roi)
        return self._apply_roi_absolute(*abs_roi)

    def schedule_roi_hardware(
        self, roi: Tuple[int, int, int, int], absolute: bool = False
    ) -> None:
        with self._roi_lock:
            self._pending_reset_resolution = None
            self._pending_hardware_roi = roi
            self._pending_roi_absolute = bool(absolute)

    def apply_pending_roi_if_any(self) -> bool:
        with self._roi_lock:
            reset = self._pending_reset_resolution
            self._pending_reset_resolution = None
            pending = self._pending_hardware_roi
            pending_absolute = self._pending_roi_absolute
            self._pending_hardware_roi = None
            self._pending_roi_absolute = False
        if reset is not None:
            ok = self._do_reset_to_resolution(reset[0], reset[1])
            if self._on_roi_applied:
                self._on_roi_applied(ok, "reset")
            return ok
        if pending is not None:
            if pending_absolute:
                ok = self._apply_roi_abs_snapped(pending)
            else:
                ok = self._apply_roi_genicam(pending)
            if self._on_roi_applied:
                self._on_roi_applied(ok, "crop")
            return ok
        return False

    def set_roi_hardware(
        self, roi: Tuple[int, int, int, int], absolute: bool = False
    ) -> bool:
        if self.cam_running_event.is_set():
            self.schedule_roi_hardware(roi, absolute=absolute)
            return True
        if absolute:
            return self._apply_roi_abs_snapped(roi)
        return self._apply_roi_genicam(roi)

    def get_max_framerate(self) -> float:
        if self._device is None:
            return float(self.config.get("FrameRate", 30))
        try:
            return float(self._device.AcquisitionFrameRate.get_range()["max"])
        except Exception:
            return self.get_actual_framerate()

    def get_measured_framerate(self) -> float:
        if len(self._frame_times) < 2:
            return 0.0
        now = time.monotonic()
        recent = [t for t in self._frame_times if t >= now - 1.0]
        if len(recent) < 2:
            return 0.0
        span = recent[-1] - recent[0]
        return (len(recent) - 1) / span if span > 0 else 0.0

    def get_actual_framerate(self) -> float:
        if self._device is None:
            return float(self.config.get("FrameRate", 30))
        try:
            return float(self._device.CurrentAcquisitionFrameRate.get())
        except Exception:
            return float(self.config.get("FrameRate", 30))

    def get_frame_id(self) -> int:
        """Frame counter of the most recent acquired frame (Galaxy Viewer 'Frame Num')."""
        return self._last_frame_id

    def get_bandwidth_bps(self) -> float:
        """Camera link throughput in bits/s (UI shows Mbps).

        Prefers GX_INT_DEVICE_LINK_CURRENT_THROUGHPUT when available.
        Fallback estimates mono8 payload: width * height * 8 * acq_fps.
        """
        if self._device is not None:
            try:
                # Galaxy DeviceLinkCurrentThroughput is typically bytes/s.
                return float(self._device.DeviceLinkCurrentThroughput.get()) * 8.0
            except Exception:
                pass
        try:
            width, height = self.get_stream_size()
            return float(width) * float(height) * 8.0 * self.get_actual_framerate()
        except Exception:
            return 0.0

    def get_actual_shutter_speed(self) -> int:
        if self._device is None:
            return int(self.config.get("ShutterSpeed", 10000))
        try:
            return int(self._device.ExposureTime.get())
        except Exception:
            return int(self.config.get("ShutterSpeed", 10000))

    def close(self) -> None:
        self.stop()
        self._device = None
        self._data_stream = None
