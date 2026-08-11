# Daheng C++ grabber — session notes (Galaxy parity)

Branch: `feature/daheng-cpp-acq-grabber` · flag: `RIO_DAHENG_CPP=1`

## Live preview (what we locked in)

- Open loads **UserSet Default** (Galaxy UserSetLoad): on MER2 ≈ AE Off, **10000 µs**, **Gain 0** → stable brightness.
- Acquisition: C++ **GXDQAllBufs** (GxViewer-style). Build `.so` with **gxbuild g++**, not Zig.
- UI exposure slider: no cam→slider→`set_exposure` loop; programmatic updates ignored.
- **Cam read: 10000 µs** in the UI is **strobe simulation**, not Daheng `ExposureTime`.
- Short exposure (e.g. 100 µs) → Acq ~228, Disp ~30 (web only). Long exposure → Acq falls as 1/Exposure.

Optional env: `RIO_DAHENG_EXPOSURE_US`, `RIO_DAHENG_AFR_MAX=1`, `RIO_DAHENG_CPP_DISPLAY_FPS`.

## ML / real-time droplet analysis

C++ does **not** block ML by itself. It helps (higher sustained Acq, less Python GIL on drain).

Watch-outs:

1. Use **raw Mono8** (`get_frame_array` / ROI), never the JPEG Disp stream, for inference.
2. Droplet code today often keeps **latest frame only** — OK at moderate rates; at high Acq + fast flow you may **drop** droplets unless you queue/process every frame (or a bounded worker pool).
3. Keep feature parity with the Python gxipy path (ROI absolute, exposure range telemetry, etc.) as ML needs them.
4. `RIO_DAHENG_CPP=0` remains a fallback if a GenICam feature is missing in the thin C++ API.
