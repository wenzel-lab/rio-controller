#!/usr/bin/env python3
"""
Probe Daheng Line1/2/3 × LineSource (ExposureActive, Strobe) for strobe sync.

Run with Rio UI stopped (exclusive camera access):

  pkill -f 'python3 main.py' || true
  cd ~/rio-controller/software
  export GALAXY_ROOT=$HOME/Galaxy_camera
  export LD_LIBRARY_PATH=$GALAXY_ROOT/lib/x86_64:$LD_LIBRARY_PATH
  export RIO_DAHENG_SN=FDQ23120254
  PYTHONPATH=. python3 scripts/probe_daheng_lineout_matrix.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gxipy as gx
from gxipy.gxidef import GxLineModeEntry, GxLineSourceEntry


SOURCES = (
    ("ExposureActive", GxLineSourceEntry.EXPOSURE_ACTIVE),
    ("Strobe", GxLineSourceEntry.STROBE),
)
LINES = (1, 2, 3)


def _enum_range(feat) -> list[str]:
    try:
        # gxipy EnumFeature: get_range() → dict symbol→value or similar
        r = feat.get_range()
        if isinstance(r, dict):
            return [f"{k}={v}" for k, v in r.items()]
        return [str(r)]
    except Exception as exc:
        return [f"<range err: {exc}>"]


def try_set(feat, value, label: str) -> tuple[bool, str]:
    try:
        feat.set(value)
        cur = feat.get()
        return True, f"ok cur={cur}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    sn = os.getenv("RIO_DAHENG_SN", "").strip() or None
    print(f"=== Daheng LineOut matrix (sn={sn or 'first'}) ===", flush=True)

    dm = gx.DeviceManager()
    dev_num, info_list = dm.update_device_list()
    if dev_num == 0:
        print("FAIL: no Daheng device")
        return 1

    cam = None
    if sn:
        for i in range(dev_num):
            info = info_list[i]
            # sn may be in sn / serial_number depending on gxipy version
            cand = (
                getattr(info, "sn", None)
                or getattr(info, "serial_number", None)
                or (info.get("sn") if isinstance(info, dict) else None)
                or ""
            )
            if str(cand) == sn:
                cam = dm.open_device_by_index(i + 1)
                break
        if cam is None:
            print(f"WARN: SN {sn} not found, opening index 1")
            cam = dm.open_device_by_index(1)
    else:
        cam = dm.open_device_by_index(1)

    print("device open", flush=True)
    remote = cam.get_remote_device_feature_control()

    # Feature access via Device attributes when available
    line_sel = getattr(cam, "LineSelector", None) or remote.get_enum_feature("LineSelector")
    line_mode = getattr(cam, "LineMode", None) or remote.get_enum_feature("LineMode")
    line_src = getattr(cam, "LineSource", None) or remote.get_enum_feature("LineSource")

    print("LineSelector range:", ", ".join(_enum_range(line_sel)), flush=True)

    results: list[tuple[int, str, bool, str]] = []
    for line in LINES:
        print(f"\n--- Line{line} ---", flush=True)
        ok_sel, msg_sel = try_set(line_sel, line, "LineSelector")
        print(f"  LineSelector={line}: {msg_sel}", flush=True)
        if not ok_sel:
            for src_name, _ in SOURCES:
                results.append((line, src_name, False, f"selector: {msg_sel}"))
            continue

        print(f"  LineMode range: {', '.join(_enum_range(line_mode))}", flush=True)
        print(f"  LineSource range: {', '.join(_enum_range(line_src))}", flush=True)

        ok_mode, msg_mode = try_set(line_mode, GxLineModeEntry.OUTPUT, "LineMode")
        print(f"  LineMode=OUTPUT: {msg_mode}", flush=True)
        if not ok_mode:
            for src_name, _ in SOURCES:
                results.append((line, src_name, False, f"mode: {msg_mode}"))
            continue

        for src_name, src_val in SOURCES:
            ok_src, msg_src = try_set(line_src, src_val, src_name)
            print(f"  LineSource={src_name}({src_val}): {msg_src}", flush=True)
            results.append((line, src_name, ok_src, msg_src))

        # restore Off if possible
        try_set(line_src, GxLineSourceEntry.OFF, "OFF")

    print("\n=== SUMMARY ===", flush=True)
    winners = []
    for line, src, ok, msg in results:
        mark = "OK " if ok else "NO "
        print(f"  {mark} Line{line} + {src}: {msg}")
        if ok:
            winners.append((line, src))

    if winners:
        # Brief stream with first winner to confirm acquisition still works
        line, src_name = winners[0]
        src_val = dict(SOURCES)[src_name]
        print(f"\nStream smoke test: Line{line} + {src_name} for 2s...", flush=True)
        try_set(line_sel, line, "sel")
        try_set(line_mode, GxLineModeEntry.OUTPUT, "mode")
        try_set(line_src, src_val, src_name)
        cam.stream_on()
        t0 = time.time()
        n = 0
        while time.time() - t0 < 2.0:
            try:
                raw = cam.data_stream[0].get_image(100)
                if raw is not None:
                    n += 1
            except Exception:
                pass
        cam.stream_off()
        try_set(line_src, GxLineSourceEntry.OFF, "OFF")
        print(f"  frames≈{n} in 2s", flush=True)
        print(
            f"\nRECOMMEND: export RIO_DAHENG_STROBE_LINE={line}  "
            f"(LineSource prefer {src_name})",
            flush=True,
        )
    else:
        print("\nNO working LineOut combination. Check Galaxy Viewer I/O page.", flush=True)

    cam.close_device()
    return 0 if winners else 2


if __name__ == "__main__":
    raise SystemExit(main())
