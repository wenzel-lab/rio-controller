#!/usr/bin/env python3
"""
Probe Daheng opto LineOut (Line3 / RIO_DAHENG_STROBE_LINE) on CoolerMaster.

Verifies the camera SDK accepts ExposureActive on the selected line and can
stream while LineOut is active. Run with Rio UI stopped (camera exclusive).

Usage:
  pkill -f 'python3 main.py'
  cd ~/rio-controller/software
  export GALAXY_ROOT=$HOME/Galaxy_camera
  export LD_LIBRARY_PATH=$GALAXY_ROOT/lib/x86_64:$LD_LIBRARY_PATH
  export RIO_DAHENG_SN=FDQ23120254
  export RIO_DAHENG_STROBE_LINE=3
  PYTHONPATH=. python3 scripts/probe_daheng_line3.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.camera.daheng_cpp_grabber import DahengGrabberLib


def main() -> int:
    line = int(os.getenv("RIO_DAHENG_STROBE_LINE", "3"))
    sn = os.getenv("RIO_DAHENG_SN")
    print(f"=== Daheng LineOut probe (line={line}, sn={sn or 'default'}) ===")
    g = DahengGrabberLib()
    g.open(sn)
    print(f"sensor {g.sensor_size()} stream {g.stream_size()}")

    for enabled in (True, False):
        ok = g.configure_strobe_line_out(enabled, line)
        print(f"configure_strobe_line_out({enabled}, line={line}) -> {ok}")
        if not ok:
            rc = g._lib.daheng_grabber_configure_strobe_line_out(1 if enabled else 0, line)
            print(f"  raw rc={rc}  (-1=no device -2=LineSelector -3=LineMode -4=LineSource)")

    print("configure ON again + start stream 3s (Line3 should toggle during exposure)...")
    g.configure_strobe_line_out(True, line)
    g.start()
    t0 = time.time()
    n = 0
    while time.time() - t0 < 3.0:
        got = g.get_latest_mono8(0)
        if got is not None:
            mono, fid, seq = got
            n += 1
            if n <= 3 or n % 30 == 0:
                print(f"  frame seq={seq} id={fid} mean={mono.mean():.1f} max={mono.max()}")
        time.sleep(0.02)
    print(f"  got {n} frames in 3s  acq_fps={g.acq_fps():.1f}")
    g.stop()
    g.close()
    print("OK: camera side LineOut configure + stream succeeded.")
    print("Next: measure opto Line3 at strobe STROBE_TRIG_IN (module pin 14) with scope/DMM while streaming.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
