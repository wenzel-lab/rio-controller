#!/usr/bin/env python3
"""Find Record ROI conditions that produce frame_id gaps."""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

SOFTWARE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOFTWARE))

os.environ.setdefault("RIO_DAHENG_CPP", "1")
os.environ.setdefault("RIO_DAHENG_SN", "FDQ23120254")
os.environ.setdefault("RIO_CAMERA_TYPE", "daheng")
os.environ.setdefault("RIO_SIMULATION", "true")
galaxy = Path.home() / "Galaxy_camera"
os.environ.setdefault("GALAXY_ROOT", str(galaxy))
os.environ["LD_LIBRARY_PATH"] = f"{galaxy}/lib/x86_64:" + os.environ.get("LD_LIBRARY_PATH", "")


def analyze(result: dict) -> dict:
    manifest = Path(result["manifest"])
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    fids = [int(r["frame_id"]) for r in rows]
    gaps = sum(int(r["gap_before"]) for r in rows)
    span_ms = 0.0
    if len(rows) >= 2:
        from datetime import datetime

        def parse_us(s: str):
            d, t, us = s.split("_")
            return datetime.strptime(f"{d}_{t}", "%Y%m%d_%H%M%S").replace(
                microsecond=int(us[:6])
            )

        span_ms = (parse_us(rows[-1]["saved_at_us"]) - parse_us(rows[0]["saved_at_us"])).total_seconds() * 1000
    return {
        "saved": result.get("frames_saved", 0),
        "requested": result.get("frames_requested", 0),
        "dropped": result.get("frames_dropped", 0),
        "overflow": result.get("queue_overflow_drops", 0),
        "gaps_sum": gaps,
        "fid_range": f"{fids[0]}..{fids[-1]}" if fids else "-",
        "span_ms": round(span_ms, 1),
        "effective_fps": round((len(rows) - 1) / (span_ms / 1000), 0) if span_ms > 0 and len(rows) > 1 else 0,
    }


def run_case(ctrl, label: str, roi, frames: int, exposure_us: float) -> dict:
    cam = ctrl.camera
    cam.set_exposure_us(exposure_us)
    time.sleep(0.3)
    if hasattr(cam, "set_roi_hardware"):
        cam.set_roi_hardware(roi, absolute=True)
        time.sleep(0.5)
    acq = round(cam.get_measured_framerate(), 1) if cam else 0
    result = ctrl.record_roi_frames(frames)
    stats = analyze(result) if result.get("manifest") else {}
    stats["label"] = label
    stats["roi"] = roi
    stats["acq_fps_before"] = acq
    stats["ok"] = result.get("ok")
    return stats


def main() -> int:
    from controllers.camera import Camera

    cases = [
        ("baseline 200x200 x50", (620, 440, 200, 200), 50, 20.0),
        ("baseline 200x200 x500", (620, 440, 200, 200), 500, 20.0),
        ("max-fps 104x80 x50", (0, 0, 104, 80), 50, 20.0),
        ("max-fps 104x80 x200", (0, 0, 104, 80), 200, 20.0),
        ("max-fps 104x80 x500", (0, 0, 104, 80), 500, 20.0),
        ("full sensor x50", (0, 0, 1440, 1080), 50, 20.0),
        ("full sensor x200", (0, 0, 1440, 1080), 200, 20.0),
    ]

    print("Stress Record ROI — gap detection\n")
    with tempfile.TemporaryDirectory() as tmp:
        with patch("controllers.camera.SNAPSHOT_FOLDER", tmp + "/"):
            exit_event = threading.Event()
            ctrl = Camera(exit_event, None)
            ctrl.initialize()
            time.sleep(0.5)

            for label, roi, n, exp in cases:
                try:
                    s = run_case(ctrl, label, roi, n, exp)
                    flag = "GAPS" if s.get("dropped", 0) > 0 or s.get("overflow", 0) > 0 else "ok"
                    print(
                        f"[{flag}] {label}: saved={s.get('saved')}/{n} dropped={s.get('dropped')} "
                        f"overflow={s.get('overflow')} acq~{s.get('acq_fps_before')}fps "
                        f"effective~{s.get('effective_fps')}fps span={s.get('span_ms')}ms fid={s.get('fid_range')}"
                    )
                except Exception as exc:
                    print(f"[ERR] {label}: {exc}")
            ctrl.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
