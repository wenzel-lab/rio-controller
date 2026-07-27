#!/usr/bin/env python3
"""
Integration tests for Daheng ROI (Galaxy SDK Roi.cpp pattern).

Requires: Galaxy SDK, camera connected, env RIO_DAHENG_SN or RIO_DAHENG_INDEX.
Run: PYTHONPATH=software GALAXY_ROOT=~/Galaxy_camera LD_LIBRARY_PATH=... python3 tests/test_daheng_roi_integration.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import CAMERA_THREAD_HEIGHT, CAMERA_THREAD_WIDTH  # noqa: F401 — kept for doc reference


def main() -> int:
    if not os.getenv("RIO_DAHENG_SN") and os.getenv("RIO_DAHENG_INDEX") is None:
        print("SKIP: set RIO_DAHENG_SN or RIO_DAHENG_INDEX")
        return 0

    from drivers.camera.daheng_camera import DahengCamera

    cam = DahengCamera()
    d = cam._device
    failures = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
        if not cond:
            failures.append(label)

    print("=== Daheng ROI integration (Galaxy SDK pattern) ===")

    # 1. Open → full sensor then config display size
    ox, oy, w, h = cam.get_sensor_roi()
    max_w, max_h = cam.get_max_resolution()
    check("open resets to full sensor width", w == max_w, f"w={w} max={max_w}")
    cam.set_config({"Width": max_w, "Height": max_h, "FrameRate": 30})
    w, h = cam.get_stream_size()
    check("display config full sensor", w == max_w and h == max_h, f"{w}x{h}")

    # 2. Stream + apply hardware ROI (view-relative crop)
    d.stream_on()
    cam.cam_running_event.set()

    view_roi = (100, 80, 400, 300)
    ok = cam._apply_roi_genicam(view_roi)
    ox, oy, aw, ah = cam.get_sensor_roi()
    check("hardware ROI apply", ok, f"Offset=({ox},{oy}) Size={aw}x{ah}")
    check("ROI width", aw == 400 or abs(aw - 400) <= 4, f"aw={aw}")
    check("ROI height", ah == 300 or abs(ah - 300) <= 4, f"ah={ah}")
    check("ROI offset X", ox == 100 or abs(ox - 100) <= 4, f"ox={ox}")
    check("ROI offset Y", oy == 80 or abs(oy - 80) <= 4, f"oy={oy}")

    img = cam._data_stream.get_image(timeout=5000)
    if img:
        arr = img.convert("RGB").get_numpy_array()
        check("frame shape matches ROI", arr.shape[1] == aw and arr.shape[0] == ah, str(arr.shape))
        mean = float(arr.mean())
        std = float(arr.std())
        check(
            "frame has signal",
            mean > 0.001 or std > 0.001 or float(arr.max()) > 0,
            f"mean={mean:.4f} std={std:.4f} max={float(arr.max()):.4f}",
        )
    else:
        check("frame received", False, "timeout")

    # 3. Clear / reset to display resolution (via capture-thread queue)
    cam.schedule_roi_reset(max_w, max_h)
    cam.apply_pending_roi_if_any()
    ox, oy, rw, rh = cam.get_sensor_roi()
    check("clear restores full sensor", rw == max_w and rh == max_h, f"{rw}x{rh}")
    check("clear resets offset", ox == 0 and oy == 0, f"({ox},{oy})")

    img2 = cam._data_stream.get_image(timeout=5000)
    if img2:
        arr2 = img2.convert("RGB").get_numpy_array()
        check("restored frame shape", arr2.shape[1] == rw and arr2.shape[0] == rh, str(arr2.shape))
    else:
        check("restored frame received", False)

    # 4. Pending ROI cancelled on clear (scheduled reset while streaming)
    cam.schedule_roi_hardware((50, 50, 200, 200))
    cam.schedule_roi_reset(max_w, max_h)
    cam.apply_pending_roi_if_any()
    rw2, rh2 = cam.get_stream_size()
    check("clear via schedule while streaming", rw2 == max_w and rh2 == max_h, f"{rw2}x{rh2}")
    ox2, oy2, _, _ = cam.get_sensor_roi()
    check("clear resets offset via schedule", ox2 == 0 and oy2 == 0, f"({ox2},{oy2})")

    d.stream_off()
    cam.close()

    print(f"\n=== {len(failures)} failure(s) ===")
    for f in failures:
        print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
