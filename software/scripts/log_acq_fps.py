#!/usr/bin/env python3
"""
Log Acq.FPS / SDK over time for Daheng Python vs C++ comparison.

Examples:
  RIO_DAHENG_CPP=1  PYTHONPATH=software ... python3 scripts/log_acq_fps.py --out /tmp/acq_cpp.csv
  (no RIO_DAHENG_CPP) PYTHONPATH=software ... python3 scripts/log_acq_fps.py --out /tmp/acq_py.csv

Close Rio / Galaxy first (exclusive camera).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seconds", type=float, default=20.0)
    p.add_argument("--interval", type=float, default=0.5)
    p.add_argument("--width", type=int, default=200)
    p.add_argument("--height", type=int, default=200)
    p.add_argument("--exposure-us", type=float, default=20.0)
    p.add_argument("--offset-x", type=int, default=620)
    p.add_argument("--offset-y", type=int, default=440)
    p.add_argument("--out", required=True, help="CSV output path")
    p.add_argument(
        "--label",
        default="",
        help="Backend label (default: cpp if RIO_DAHENG_CPP else python)",
    )
    args = p.parse_args()

    use_cpp = os.getenv("RIO_DAHENG_CPP", "").strip().lower() in ("1", "true", "yes", "on")
    label = args.label or ("cpp" if use_cpp else "python")

    # Ensure software on path when run from repo root
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    from drivers.camera.camera_base import _create_daheng_camera

    cam = _create_daheng_camera()
    backend = type(cam).__name__
    roi = (args.offset_x, args.offset_y, args.width, args.height)
    if hasattr(cam, "set_roi_hardware"):
        cam.set_roi_hardware(roi, absolute=True)
    if hasattr(cam, "set_exposure_us"):
        cam.set_exposure_us(args.exposure_us)

    # Drive acquisition
    gen = cam.generate_frames()
    t0 = time.monotonic()
    next_jpeg = t0
    rows = []
    print(f"logging label={label} backend={backend} for {args.seconds}s → {args.out}")

    while True:
        now = time.monotonic()
        elapsed = now - t0
        if elapsed >= args.seconds:
            break
        # Keep generator alive (display path)
        if now >= next_jpeg:
            try:
                next(gen)
            except StopIteration:
                break
            next_jpeg = now + 0.1
        acq = float(cam.get_measured_framerate()) if hasattr(cam, "get_measured_framerate") else 0.0
        sdk = float(cam.get_actual_framerate()) if hasattr(cam, "get_actual_framerate") else 0.0
        # Host drain from wall-clock note times in last 1s (avoids frame_id catch-up spikes).
        count_fps = 0.0
        times = list(getattr(cam, "_frame_times", []) or [])
        recent = [t for t in times if t >= now - 1.0]
        if len(recent) >= 2:
            span = recent[-1] - recent[0]
            if span > 0:
                count_fps = (len(recent) - 1) / span
        if use_cpp and acq > 0:
            count_fps = acq
        rows.append(
            {
                "t_s": round(elapsed, 3),
                "acq_fps": round(acq, 2),
                "count_fps": round(count_fps, 2),
                "sdk_fps": round(sdk, 2),
                "label": label,
                "backend": backend,
            }
        )
        time.sleep(args.interval)

    try:
        cam.close()
    except Exception:
        pass

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["t_s", "acq_fps", "count_fps", "sdk_fps", "label", "backend"]
        )
        w.writeheader()
        w.writerows(rows)

    counts = [r["count_fps"] for r in rows if r["count_fps"] > 0]
    if counts:
        print(
            f"done n={len(rows)} count_fps mean={sum(counts)/len(counts):.2f} "
            f"min={min(counts):.2f} max={max(counts):.2f}"
        )
    else:
        print(f"done n={len(rows)} (no non-zero count_fps samples yet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
