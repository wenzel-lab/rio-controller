# software/droplet-detection/ — Droplet detection pipeline

This folder contains the droplet detection algorithm (classical CV pipeline) plus offline utilities (tests/benchmarking/parameter search).

## How it fits into the running system (interfaces)

At runtime this folder is used by:

- `software/controllers/droplet_detector_controller.py`
  - constructs `DropletDetector(roi, config, radius_offset_px=...)`
  - pulls ROI frames from the camera stack and calls `DropletDetector.process_frame(...)`
  - aggregates results into a `DropletHistogram` and exposes status/stats/export helpers
- `software/rio-webapp/controllers/droplet_web_controller.py`
  - WebSocket command handler (`"droplet"` event) that calls controller methods like `start()`, `stop()`, `update_config(...)`, `load_profile(...)`
- `software/rio-webapp/routes.py`
  - optional HTTP API endpoints under `/api/droplet/*` (status/histogram/statistics/performance/start/stop/config/profile/export)

## Data flow (runtime)

- **ROI selection**: browser UI selects ROI → stored by `software/controllers/camera.py` (see `Camera.get_roi()`).
- **Start detection**: UI sends `"droplet": {"cmd": "start"}` → `DropletDetectorController.start()` reads current ROI and creates a detector.
- **Frame processing**: ROI frames (RGB numpy arrays) are processed:
  1. preprocess → binary mask
  2. contour segmentation
  3. artifact rejection (temporal/motion filtering)
  4. measurement (per-droplet metrics)
  5. histogram/statistics update
- **Reporting**: histogram/statistics are emitted periodically to the UI and are also available via HTTP.

## What’s inside (key modules)

- **Pipeline orchestrator**: `detector.py`
  - `class DropletDetector(roi, config, radius_offset_px=0.0)`
  - `process_frame(frame, timing_callback=None) -> list[DropletMetrics]`
- **Preprocessing**: `preprocessor.py`
  - background correction: `background_method = "static" | "highpass"`
  - thresholding: `threshold_method = "otsu" | "adaptive"`
  - morphology: `morph_operation = "open" | "close" | "both"`
- **Segmentation**: `segmenter.py`
  - `cv2.findContours` + filtering by `min_area/max_area` and `min_aspect_ratio/max_aspect_ratio`
  - optional “channel band” filtering around a `(y_min, y_max)` corridor
- **Artifact rejection**: `artifact_rejector.py`
  - centroid-based motion validation (assumes downstream motion is \(+x\))
  - optional frame-difference gate (`use_frame_diff`)
- **Measurement**: `measurer.py`
  - `DropletMetrics` dataclass: `area`, `major_axis`, `equivalent_diameter`, `centroid`, `bounding_box`, `aspect_ratio`
  - ellipse fitting when possible (`cv2.fitEllipse`), with bounding-box fallback
  - optional `radius_offset_px` correction applied to diameter-like measurements
- **Histogram/statistics**: `histogram.py`
  - `DropletHistogram(maxlen, bins, pixel_ratio, unit)` keeps a sliding window of measurements and produces UI-friendly stats
- **Config + profiles**: `config.py`
  - `DropletDetectionConfig` holds tunables for all stages
  - `load_config(path)`, `save_config(path, config)`, `extract_droplet_config(config_dict)` support nested config files

## “Importing this module” (practical note)

The folder name is `droplet-detection/` but runtime imports typically load it as the module name `droplet_detection` via `importlib` (see `software/controllers/droplet_detector_controller.py` and some tests). Keep that coupling in mind if you rename/move the folder.

## Offline tooling in this folder

- **Unit/integration tests**: `test_detector.py`, `test_integration.py`, `run_tests.sh`
- **Benchmark**: `benchmark.py` generates synthetic frames and times each pipeline stage
- **Parameter search**: `optimize.py` runs a grid search against a dataset (via `test_data_loader.py`)
- **Dataset helpers**: `test_data_loader.py` looks for a `droplet_AInalysis` checkout to source real test images

## Running tests (simulation-friendly)

From `software/` (preferred):

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```

Droplet-detection specific guidance lives in `software/tests/droplet-detection-testing_and_optimization_guide.md`.

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change pipeline behavior, interfaces, or event/API contracts, update this document.


