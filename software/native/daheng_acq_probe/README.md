# Daheng C++ Acq.FPS probe

Branch spike on `feature/daheng-cpp-acq-grabber`: measure whether a **native** Galaxy-style drain (`GXDQAllBufs` + 8 MiB buffer pool, **no** RGB/JPEG) can hold Acq ≈ SDK (~1050 @ 200×200 / 20 µs).

This does **not** replace Rio yet — standalone binary only. Close Rio and Galaxy Viewer before running (exclusive USB).

## Branch comparison (Python vs C++)

| Branch | What to run | Typical result (same scene) |
|---|---|---|
| `feature/daheng-python-acq-ab` | Rio UI → 200×200 @ 20 µs | Acq ~960, SDK ~1053 |
| `feature/daheng-cpp-acq-grabber` | this probe (below) | Acq ~1052–1054 ≈ SDK |

### Python-only (Rio)

```bash
git checkout feature/daheng-python-acq-ab
# start Rio as usual (RIO_CAMERA_TYPE=daheng, etc.)
# UI: http://localhost:5000 — apply ROI 200×200, exposure 20 µs, note Acq.FPS / SDK
```

### C++ probe (this branch)

```bash
git checkout feature/daheng-cpp-acq-grabber
pkill -f 'venv-daheng/bin/python3 main.py' || true   # camera is exclusive
cd software/native/daheng_acq_probe
# build (see below), then:
./daheng_acq_probe --sn FDQ23120254 --width 200 --height 200 --exposure-us 20 --seconds 15
```

Compare per-second **Acq.FPS** to **SDK** on both paths. Do not run Rio and the probe at the same time.

## Build

```bash
cd software/native/daheng_acq_probe
make   # needs system g++/make
# or without apt packages (Zig user install):
ZIG=~/.local/opt/zig-linux-x86_64-0.13.0/zig
GALAXY_ROOT=$HOME/Galaxy_camera
$ZIG c++ -O2 -std=c++17 -I$GALAXY_ROOT/inc -o daheng_acq_probe daheng_acq_probe.cpp \
  -L$GALAXY_ROOT/lib/x86_64 -Wl,-rpath,$GALAXY_ROOT/lib/x86_64 -lgxiapi -lpthread
```

**Measured (CoolerMaster, MER2 SN FDQ23120254, 200×200 @ 20 µs, 15 s):** per-second Acq ≈ **1052–1054** matching SDK **1052.63**, incomplete=0. Python Rio on `feature/daheng-python-acq-ab` sustained ~960 under the same scene.

## Run

```bash
# Stop Rio first
pkill -f 'venv-daheng/bin/python3 main.py' || true

make run
# or:
./daheng_acq_probe --sn FDQ23120254 --width 200 --height 200 --exposure-us 20 --seconds 15
```

## Success criterion

Mean **Acq.FPS** within ~1–2 % of **SDK** (e.g. ≥1035 if SDK≈1053) over 15 s, without large incomplete-frame counts.

If yes → worth a thin C++ grabber behind Python later (`RIO_DAHENG_CPP=1` on this branch).  
If no → bottleneck is elsewhere (USB/host), not Python alone.
