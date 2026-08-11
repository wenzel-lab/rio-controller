#!/usr/bin/env python3
"""Diagnose Daheng CPP brightness / exposure after open and AFR sync."""
import os
import sys
import time

import numpy as np

os.environ.setdefault("GALAXY_ROOT", os.path.expanduser("~/Galaxy_camera"))
os.environ["LD_LIBRARY_PATH"] = (
    os.environ["GALAXY_ROOT"]
    + "/lib/x86_64:"
    + "/home/tobias-wenzel/rio-controller/software/native/daheng_grabber:"
    + os.environ.get("LD_LIBRARY_PATH", "")
)
sys.path.insert(0, "/home/tobias-wenzel/rio-controller/software")

from drivers.camera.daheng_cpp_grabber import DahengCppGrabber  # noqa: E402


def sample(g, n=50):
    means = []
    seq = 0
    for _ in range(n * 3):
        if len(means) >= n:
            break
        got = g.get_latest_mono8(seq)
        if got is None:
            time.sleep(0.005)
            continue
        mono, _fid, seq = got
        means.append(float(mono.mean()))
    a = np.asarray(means, dtype=np.float64)
    if a.size == 0:
        return {"n": 0}
    return {
        "n": int(a.size),
        "mean": float(a.mean()),
        "std": float(a.std()),
        "min": float(a.min()),
        "max": float(a.max()),
    }


def main() -> None:
    g = DahengCppGrabber()
    g.open("FDQ23120254")
    print("opened exposure_us=", g.get_exposure_us(), "sdk_fps=", g.sdk_fps(), flush=True)
    g.start()
    time.sleep(0.4)
    print("sample@open", sample(g), flush=True)

    for us in (20.0, 100.0, 1000.0, 10000.0):
        g.set_exposure_us(us)
        time.sleep(0.35)
        print(
            f"set {us} -> read {g.get_exposure_us():.1f} sdk={g.sdk_fps():.1f}",
            sample(g),
            flush=True,
        )

    g.sync_afr_max()
    time.sleep(0.35)
    print(
        "after sync_afr_max exposure=",
        g.get_exposure_us(),
        "sdk=",
        g.sdk_fps(),
        sample(g),
        flush=True,
    )
    g.close()
    print("done", flush=True)


if __name__ == "__main__":
    main()
