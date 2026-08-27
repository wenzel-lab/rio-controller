#!/usr/bin/env python3
"""Strobe PIC diagnostics (firmware v3, SPI packet 6).

Runs on the Raspberry Pi with the Rio API stopped, since SPI access is exclusive.
Drives the strobe directly over SPI and polls the firmware counters, so the
camera signal path can be verified without a scope:

  level     1 = idle (internal pull-up), 0 = camera asserting exposure
  edges     increments on every transition seen on the trigger pin
  fired     increments every time the firmware actually flashes the LED
  gap_us    time the line stayed high before the last falling edge, i.e. the
            camera readout gap (65535 means the 16-bit timer saturated)

Usage (on Pi):
    pkill -f 'python3 -m api.main'
    cd ~/rio-controller

    # LED path check, no camera needed
    PYTHONPATH=. RIO_SIMULATION=false python3 scripts/probe_strobe_diag.py --self-test

    # visible free-run blink (~8 Hz), no camera needed
    PYTHONPATH=. RIO_SIMULATION=false python3 scripts/probe_strobe_diag.py --free-run --seconds 10

    # hardware trigger while the host streams the camera
    PYTHONPATH=. RIO_SIMULATION=false python3 scripts/probe_strobe_diag.py --seconds 30
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import STROBE_REPLY_PAUSE_S  # noqa: E402
from drivers.spi_handler import PORT_STROBE, spi_init  # noqa: E402
from drivers.strobe import PiStrobe  # noqa: E402

# Free-run needs tens of ms per phase to be visible as a blink rather than a
# steady dim glow; hardware trigger wants a short flash inside one exposure.
FREE_RUN_WAIT_US = 60_000
FREE_RUN_FLASH_US = 60_000
TRIGGER_WAIT_US = 32
TRIGGER_FLASH_US = 1_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=30.0, help="polling duration")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between reads")
    parser.add_argument("--flash-us", type=int, default=None, help="flash width in us")
    parser.add_argument("--wait-us", type=int, default=None, help="wait before flash in us")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the firmware LED blink test and exit",
    )
    parser.add_argument(
        "--free-run",
        action="store_true",
        help="use software free-run instead of hardware trigger",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    spi_init(0, 2, 30000)
    strobe = PiStrobe(PORT_STROBE, STROBE_REPLY_PAUSE_S)

    diag = strobe.get_diag()
    if diag is None:
        print("FAIL: firmware does not answer packet 6 (GET_DIAG).")
        print("Flash firmware v3 from hardware-modules/strobe-imaging/strobe_pic/.")
        return 1

    print(f"firmware version = {diag['version']}")
    print(f"trigger pin level now = {diag['trig_level']} (expect 1 with the camera idle)")

    if args.self_test:
        print("Running LED self-test: 5 blinks of 250 ms. Watch the LED.")
        ok = strobe.self_test()
        time.sleep(3.0)
        print(f"self_test acknowledged = {ok}")
        return 0 if ok else 1

    hardware = not args.free_run
    wait_us = args.wait_us
    flash_us = args.flash_us
    if wait_us is None:
        wait_us = TRIGGER_WAIT_US if hardware else FREE_RUN_WAIT_US
    if flash_us is None:
        flash_us = TRIGGER_FLASH_US if hardware else FREE_RUN_FLASH_US

    strobe.set_hold(False)
    strobe.set_trigger_mode(hardware)
    ok_timing, actual_wait_ns, actual_flash_ns = strobe.set_timing(wait_us * 1000, flash_us * 1000)
    strobe.set_enable(True)

    mode = "hardware trigger" if hardware else "software free-run"
    print(f"mode = {mode}, timing ok = {ok_timing}")
    print(f"wait = {actual_wait_ns / 1000:.0f} us, flash = {actual_flash_ns / 1000:.0f} us")
    if hardware:
        print("Start the camera stream on the host now.")
    else:
        cycle_hz = 1e6 / max(wait_us + flash_us, 1)
        print(f"Expect a visible blink near {cycle_hz:.1f} Hz.")

    header = f"{'t':>6}  {'level':>5}  {'edges':>7}  {'fired':>7}  {'edges/s':>8}  {'fired/s':>8}  {'gap_us':>7}"
    print(header)

    start = time.monotonic()
    baseline = strobe.get_diag() or diag
    prev = baseline
    prev_t = start

    while time.monotonic() - start < args.seconds:
        time.sleep(args.interval)
        now = time.monotonic()
        current = strobe.get_diag()
        if current is None:
            print("read failed")
            continue
        _, gap_us = strobe.get_cam_read_time()
        dt = max(now - prev_t, 1e-6)
        d_edges = (current["edge_count"] - prev["edge_count"]) & 0xFFFF
        d_fired = (current["trigger_count"] - prev["trigger_count"]) & 0xFFFF
        print(
            f"{now - start:6.1f}  {current['trig_level']:>5}  {current['edge_count']:>7}  "
            f"{current['trigger_count']:>7}  {d_edges / dt:8.1f}  {d_fired / dt:8.1f}  {gap_us:>7}"
        )
        prev, prev_t = current, now

    strobe.set_enable(False)
    strobe.set_trigger_mode(False)

    final = strobe.get_diag() or {}
    total_edges = (final.get("edge_count", 0) - baseline["edge_count"]) & 0xFFFF
    total_fired = (final.get("trigger_count", 0) - baseline["trigger_count"]) & 0xFFFF
    print(f"\ntotal edges = {total_edges}, total flashes = {total_fired}")

    if not hardware:
        if total_fired == 0:
            print("VERDICT: free-run never fired. Firmware or SPI issue, not the camera.")
        else:
            print("VERDICT: firmware fires on its own. If the LED stayed dark, the")
            print("         problem is the LED drive, not the trigger path.")
        return 0

    if total_edges == 0:
        print("VERDICT: no edges on the trigger pin. Signal or wiring, not the firmware.")
        print("Next: inject a synthetic trigger from a Pi GPIO to isolate camera vs cabling.")
    elif total_fired == 0:
        print("VERDICT: edges arrive but the firmware never fires. Trigger logic issue.")
    else:
        print("VERDICT: trigger path works. If the LED looks dark, check flash width.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
