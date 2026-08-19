#!/usr/bin/env python3
"""Sweep hardware ROI vs Acq.FPS using daheng_acq_probe (manuscript: 1000 fps / 300x100).

Close Rio / Galaxy first. Exposure default 20 µs (same as 200x200 probe).
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "daheng_acq_probe" / "daheng_acq_probe"
OUT = Path(__file__).resolve().parent / "roi_acq_sweep_20us.csv"

# Width % 4 == 0, height % 2 == 0 (GxIAPI). Centered inside probe.
ROIS = [
    (1440, 1080),  # MER2-160 full
    (1280, 720),
    (800, 600),
    (640, 480),
    (400, 300),
    (320, 240),  # Mako comparison point in the todo doc
    (300, 100),  # explicit manuscript question
    (200, 200),  # known ~1050
    (160, 120),
    (100, 80),
]

SUMMARY_RE = re.compile(
    r"mean Acq\.FPS=([0-9.]+)\s+last_window=([0-9.]+)\s+SDK=([0-9.]+)"
    r"\s+frames=(\d+)\s+incomplete=(\d+)"
)
ROI_RE = re.compile(r"ROI=(\d+)x(\d+) @ offset\((\d+),(\d+)\) exposure=([0-9.]+) us")


def main() -> int:
    seconds = 8.0
    exposure_us = 20.0
    sn = "FDQ23120254"
    if not PROBE.is_file():
        print(f"missing probe: {PROBE}", file=sys.stderr)
        return 1

    rows = []
    print(f"sweep {len(ROIS)} ROIs × {seconds:.0f}s @ {exposure_us:.0f} µs → {OUT}", flush=True)
    for w, h in ROIS:
        print(f"\n=== {w}x{h} ===", flush=True)
        proc = subprocess.run(
            [
                str(PROBE),
                "--sn",
                sn,
                "--width",
                str(w),
                "--height",
                str(h),
                "--exposure-us",
                str(exposure_us),
                "--seconds",
                str(seconds),
            ],
            cwd=str(PROBE.parent),
            capture_output=True,
            text=True,
        )
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        print(text.strip()[-800:], flush=True)
        m = SUMMARY_RE.search(text)
        r = ROI_RE.search(text)
        if proc.returncode != 0 or not m:
            rows.append(
                {
                    "width": w,
                    "height": h,
                    "pixels": w * h,
                    "offset_x": "",
                    "offset_y": "",
                    "exposure_us": exposure_us,
                    "acq_fps": "",
                    "sdk_fps": "",
                    "frames": "",
                    "incomplete": "",
                    "ok": 0,
                    "error": (proc.stderr or proc.stdout or "fail")[-200:],
                }
            )
            continue
        ox = oy = ""
        exp = exposure_us
        if r:
            w, h = int(r.group(1)), int(r.group(2))
            ox, oy = int(r.group(3)), int(r.group(4))
            exp = float(r.group(5))
        acq = float(m.group(1))
        sdk = float(m.group(3))
        rows.append(
            {
                "width": w,
                "height": h,
                "pixels": w * h,
                "offset_x": ox,
                "offset_y": oy,
                "exposure_us": exp,
                "acq_fps": round(acq, 2),
                "sdk_fps": round(sdk, 2),
                "frames": int(m.group(4)),
                "incomplete": int(m.group(5)),
                "ok": 1,
                "error": "",
            }
        )

    with OUT.open("w", newline="") as f:
        wri = csv.DictWriter(
            f,
            fieldnames=[
                "width",
                "height",
                "pixels",
                "offset_x",
                "offset_y",
                "exposure_us",
                "acq_fps",
                "sdk_fps",
                "frames",
                "incomplete",
                "ok",
                "error",
            ],
        )
        wri.writeheader()
        wri.writerows(rows)

    print("\n=== TABLE ===")
    print(f"{'ROI':>12}  {'px':>8}  {'Acq':>8}  {'SDK':>8}")
    for row in rows:
        if row["ok"]:
            print(
                f"{row['width']}x{row['height']:>4}  {row['pixels']:8d}  "
                f"{row['acq_fps']:8.1f}  {row['sdk_fps']:8.1f}"
            )
        else:
            print(f"{row['width']}x{row['height']:>4}  FAIL {row['error'][:60]}")
    ge1000 = [r for r in rows if r["ok"] and float(r["acq_fps"]) >= 1000]
    if ge1000:
        biggest = max(ge1000, key=lambda r: r["pixels"])
        print(
            f"\nLargest ROI with Acq≥1000: {biggest['width']}x{biggest['height']} "
            f"({biggest['pixels']} px) Acq={biggest['acq_fps']}"
        )
    rect = next((r for r in rows if r["width"] == 300 and r["height"] == 100), None)
    if rect:
        print(f"300x100 rectangular: ok={rect['ok']} Acq={rect['acq_fps']} SDK={rect['sdk_fps']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
