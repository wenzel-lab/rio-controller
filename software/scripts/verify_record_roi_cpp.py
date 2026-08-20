#!/usr/bin/env python3
"""Verify Record ROI: unique frame_ids, manifest, drop stats."""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import threading
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


def main() -> int:
    from controllers.camera import Camera
    from drivers.camera.daheng_cpp_grabber import DahengGrabberLib

    g = DahengGrabberLib()
    has_queue = getattr(g, "_has_record_queue", False)
    print(f"record_queue in .so: {has_queue}")

    with tempfile.TemporaryDirectory() as tmp:
        with patch("controllers.camera.SNAPSHOT_FOLDER", tmp + "/"):
            exit_event = threading.Event()
            ctrl = Camera(exit_event, None)
            ctrl.initialize()
            import time

            time.sleep(0.5)
            result = ctrl.record_roi_frames(50)
            print("result:", {k: result[k] for k in result if k != "error" or result[k]})

            if not result.get("ok") or result.get("frames_saved") != 50:
                ctrl.close()
                return 1

            manifest = Path(result["manifest"])
            rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
            fids = [int(r["frame_id"]) for r in rows]
            gaps = sum(int(r["gap_before"]) for r in rows)
            unique_fids = len(set(fids))
            consecutive = all(b - a == 1 for a, b in zip(fids, fids[1:]))

            print(f"manifest rows: {len(rows)} unique frame_id: {unique_fids}")
            print(f"frame_id range: {fids[0]}..{fids[-1]} gaps_sum: {gaps} consecutive: {consecutive}")
            print(f"frames_dropped: {result.get('frames_dropped')} queue_overflow: {result.get('queue_overflow_drops')}")

            ctrl.close()

            if unique_fids != 50:
                print("FAIL: frame_ids not all unique")
                return 1
            if gaps != result.get("frames_dropped", -1):
                print("FAIL: gap accounting mismatch")
                return 1
            if not has_queue and gaps > 0:
                print(f"WARN: {gaps} drops without record queue (.so rebuild recommended)")
            elif gaps > 0 or result.get("queue_overflow_drops", 0) > 0:
                print(f"FAIL: drops detected gaps={gaps} overflow={result.get('queue_overflow_drops')}")
                return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
