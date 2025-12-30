# Testing and Optimization Guide
## Droplet Detection System

**Date:** December 2025  
**Status:** Complete

---

## Overview

This guide describes the testing and optimization tools available for the droplet detection system. These tools help validate correctness, measure performance, and optimize parameters.

---

## Testing Tools

### 1. Unit Tests

**Location:** `software/tests/test_droplet_detection.py`

**Run:**
```bash
cd software
python -m unittest discover -s tests -p "test_droplet_detection.py" -v
```

**Or with pytest:**
```bash
python -m pytest tests/test_droplet_detection.py -v
```

**Coverage:**
- Configuration management
- Preprocessor
- Segmenter
- Measurer
- ArtifactRejector
- Histogram
- Detector (full pipeline)
- Integration tests

### 2. Integration Tests

**Location:** `software/droplet-detection/test_integration.py`

**Run:**
```bash
cd software
python -m droplet_detection.test_integration --images 10
```

**Tests:**
- Configuration loading and validation
- Histogram generation
- Full detection pipeline on real images
- Statistics calculation

**Requirements:**
- Test images from `droplet_AInalysis/imgs` (optional, will skip if not available)

### 3. Test Runner Script

**Location:** `software/droplet-detection/run_tests.sh`

**Run:**
```bash
cd software/droplet-detection
./run_tests.sh
```

**Features:**
- Automatically activates mamba `rio-simulation` environment
- Runs both unit and integration tests
- Handles missing dependencies gracefully

---

## Performance Benchmarking

### Benchmark Script

**Location:** `software/droplet-detection/benchmark.py`

**Purpose:** Measure processing speed with various ROI sizes and droplet densities.

**Usage:**
```bash
cd software
python -m droplet_detection.benchmark [options]
```

**Options:**
- `--roi-size SMALL|MEDIUM|LARGE|all` - ROI size to test (default: all)
- `--density LOW|MEDIUM|HIGH|all` - Droplet density to test (default: all)
- `--iterations N` - Number of iterations per test (default: 100)
- `--output FILE` - Output JSON file (default: benchmark_results.json)

**Example:**
```bash
# Test all scenarios
python -m droplet_detection.benchmark --iterations 200

# Test only small ROI with low density
python -m droplet_detection.benchmark --roi-size small --density low

# Custom output file
python -m droplet_detection.benchmark --output my_benchmark.json
```

**Output:**
- Console summary with timing statistics
- JSON file with detailed results
- Frame rate limit recommendations

**Metrics Measured:**
- Preprocessing time (background correction + thresholding)
- Segmentation time (contour detection + filtering)
- Measurement time (geometric metrics)
- Artifact rejection time
- Histogram update time
- Total per-frame processing time
- Frame rate limits (max FPS, safe FPS)

**ROI Sizes:**
- Small: 50×256 px
- Medium: 100×512 px
- Large: 150×1024 px

**Droplet Densities:**
- Low: 1-5 droplets/frame
- Medium: 5-20 droplets/frame
- High: 20-50 droplets/frame

---

## Parameter Optimization

### Optimization Script

**Location:** `software/droplet-detection/optimize.py`

**Purpose:** Find optimal parameter configurations using grid search.

**Usage:**
```bash
cd software
python -m droplet_detection.optimize [options]
```

**Options:**
- `--dataset PATH` - Path to test image dataset (default: droplet_AInalysis/imgs)
- `--max-images N` - Maximum number of test images (default: 20)
- `--output FILE` - Output JSON file (default: optimized_config.json)
- `--top-k N` - Number of top configurations to save (default: 10)
- `--base-config PATH` - Base configuration JSON file (optional)

**Example:**
```bash
# Optimize with default settings
python -m droplet_detection.optimize

# Use specific dataset
python -m droplet_detection.optimize --dataset /path/to/images --max-images 30

# Start from existing config
python -m droplet_detection.optimize --base-config my_config.json
```

**Output:**
- Console summary of top configurations
- JSON file with all top-k results
- Best configuration saved as `*_best_config.json`

**Parameters Optimized:**
- `min_area`: [10, 20, 30, 50]
- `max_area`: [1000, 2000, 5000, 10000]
- `threshold_method`: ['otsu', 'adaptive']
- `background_method`: ['static', 'highpass']
- `morph_kernel_size`: [3, 5]

**Evaluation Metrics:**
- Detection rate
- False positive rate
- False negative rate
- Average droplets per frame
- Combined score (for ranking)

**Note:** This tool is designed to run offline on a PC with test images. It performs grid search over the parameter space, which can be computationally intensive.

---

## Performance Monitoring (Runtime)

### Timing Instrumentation

The `DropletDetectorController` includes built-in timing instrumentation:

```python
from controllers.droplet_detector_controller import DropletDetectorController

controller = DropletDetectorController(camera, strobe_cam)

# Start detection
controller.start()

# ... after some processing ...

# Get performance metrics
metrics = controller.get_performance_metrics()
print(metrics)
```

**Metrics Available:**
- Component-level timing (preprocessing, segmentation, etc.)
- Per-frame total time
- Statistics (mean, std, min, max, p95, p99)
- Frame rate calculations

### Web API

Performance metrics are also available via REST API:

```bash
curl http://localhost:5000/api/droplet/performance
```

**Response:**
```json
{
  "preprocessing": {
    "mean": 5.2,
    "std": 0.8,
    "min": 4.1,
    "max": 7.3,
    "p95": 6.5,
    "p99": 7.0,
    "count": 1000
  },
  ...
  "frame_rate": {
    "current_fps": 15.2,
    "max_fps": 18.5,
    "safe_fps": 16.0
  }
}
```

---

## Test Data

### Using droplet_AInalysis Images

The system can use test images from the `droplet_AInalysis` repository:

**Location:** `droplet_AInalysis/imgs/`

**Supported Formats:**
- `.jpg`, `.jpeg`
- `.png`
- `.bmp`

**Automatic Detection:**
- Scripts automatically search for `droplet_AInalysis` relative to the workspace
- Falls back gracefully if images are not available

### Synthetic Test Data

The benchmark script generates synthetic test frames with:
- Configurable ROI size
- Configurable number of droplets
- Realistic noise and background variation
- Elliptical droplets (dark on light background)

---

## Interpreting Results

### Benchmark Results

**Key Metrics:**
- **Mean time**: Average processing time (most important)
- **P95 time**: 95th percentile (safe frame rate calculation)
- **P99 time**: 99th percentile (worst-case scenario)
- **Max FPS**: Theoretical maximum (based on mean)
- **Safe FPS**: Recommended maximum (based on P95)

**Example:**
```
Scenario: ROI=medium (100×512), Density=medium (12 droplets)
  preprocessing          : mean= 5.23ms, std= 0.45ms, p95= 6.12ms
  segmentation          : mean= 8.67ms, std= 1.23ms, p95=10.45ms
  measurement           : mean= 2.34ms, std= 0.34ms, p95= 2.89ms
  total_per_frame       : mean=18.45ms, std= 2.12ms, p95=22.34ms

  Frame Rate Limits:
    Max FPS: 54.2
    Safe FPS: 44.8 (p95)
```

**Recommendation:** Use Safe FPS for sustained operation.

### Optimization Results

**Top Configurations:**
- Ranked by combined score (higher is better)
- Score considers detection rate, FPR, and FNR
- Best configuration saved automatically

**Example:**
```
1. Score: 0.892
   Detection Rate: 0.950
   False Positive Rate: 0.050
   False Negative Rate: 0.030
   Avg Droplets/Frame: 12.34
   Config: min_area=20, max_area=5000, threshold=otsu, background=static
```

---

## Best Practices

### 1. Testing Before Deployment
- Run unit tests to verify correctness
- Run integration tests with real images
- Run benchmarks to establish baseline performance

### 2. Parameter Tuning
- Start with default configuration
- Use optimization tool to find better parameters for your specific setup
- Validate optimized parameters with integration tests

### 3. Performance Monitoring
- Monitor timing metrics during runtime
- Use Safe FPS for frame rate limits
- Adjust ROI size if performance is insufficient

### 4. Continuous Testing
- Run tests after code changes
- Re-benchmark after hardware changes
- Re-optimize when experimental conditions change

---

## Troubleshooting

### Tests Fail to Run
- **Issue:** Missing dependencies
- **Solution:** Activate mamba `rio-simulation` environment
- **Check:** `python -c "import cv2, numpy"`

### No Test Images Found
- **Issue:** Integration tests skip image tests
- **Solution:** Ensure `droplet_AInalysis/imgs` exists or provide `--dataset` path
- **Note:** Unit tests don't require images

### Benchmark Takes Too Long
- **Issue:** Too many iterations or scenarios
- **Solution:** Reduce `--iterations` or test specific `--roi-size` and `--density`

### Optimization Takes Too Long
- **Issue:** Large parameter grid
- **Solution:** Reduce `--max-images` or provide `--base-config` to narrow search

---

## Next Steps

After testing and optimization:

1. **Document Results:** Save benchmark and optimization results to a local folder (or external lab notebook) and avoid committing large artifacts to the repository
2. **Create Profiles:** Save optimized configurations as parameter profiles
3. **Validate on Hardware:** Test optimized parameters on actual Raspberry Pi
4. **Monitor Runtime:** Use timing instrumentation to verify performance in production

---

## Files Reference

- `software/tests/test_droplet_detection.py` - Unit tests
- `software/droplet-detection/test_integration.py` - Integration tests
- `software/droplet-detection/benchmark.py` - Performance benchmarking
- `software/droplet-detection/optimize.py` - Parameter optimization
- `software/droplet-detection/run_tests.sh` - Test runner script
- `software/controllers/droplet_detector_controller.py` - Runtime timing instrumentation

---

**Status:** ✅ Testing and optimization tools complete and ready for use.
