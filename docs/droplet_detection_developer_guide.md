# Droplet Detection Developer Guide
## Architecture and Extension Points

**Version:** 1.0  
**Date:** December 2025

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Structure](#module-structure)
3. [Core Components](#core-components)
4. [Extension Points](#extension-points)
5. [Adding New Features](#adding-new-features)
6. [Testing](#testing)
7. [Code Style](#code-style)

---

## Architecture Overview

The droplet detection system follows a modular pipeline architecture:

```
Camera → ROI Frame → Preprocessor → Segmenter → Measurer → ArtifactRejector → Histogram
                                                                    ↓
                                                              DropletMetrics
```

### Design Principles

1. **Modularity:** Each component is independent and testable
2. **Pi Compatibility:** Works on both 32-bit and 64-bit Raspberry Pi OS
3. **Performance:** Optimized for real-time processing
4. **Extensibility:** Easy to add new algorithms or features

### Integration Points

- **Camera System:** Uses existing `Camera` and `PiStrobeCam` classes
- **Web Interface:** Integrates with Flask + SocketIO
- **Configuration:** JSON-based parameter management

---

## Module Structure

### Package: `droplet-detection/`

```
droplet-detection/
├── __init__.py              # Package exports
├── config.py                # Configuration management
├── detector.py              # Main pipeline orchestrator
├── preprocessor.py          # Image preprocessing
├── segmenter.py             # Contour detection
├── measurer.py              # Geometric measurements
├── artifact_rejector.py     # Temporal filtering
├── histogram.py             # Statistics and histograms
├── utils.py                 # Utility functions
├── benchmark.py             # Performance benchmarking
├── optimize.py              # Parameter optimization
├── test_integration.py      # Integration tests
└── test_data_loader.py      # Test image loading
```

### Controller: `controllers/droplet_detector_controller.py`

- Business logic for real-time detection
- Threading and frame queue management
- Performance instrumentation
- Integration with camera system

### Web Controller: `rio-webapp/controllers/droplet_web_controller.py`

- WebSocket event handlers
- REST API endpoints (in `routes.py`)
- Rate-limited updates

---

## Core Components

### 1. DropletDetectionConfig (`config.py`)

**Purpose:** Centralized parameter management

**Key Methods:**
- `update(config_dict)` - Update parameters
- `validate()` - Validate parameter values
- `to_dict()` - Serialize to dictionary
- `save_config()` / `load_config()` - File I/O

**Extension:** Add new parameters by:
1. Adding attribute to `__init__`
2. Adding validation in `validate()`
3. Updating `to_dict()` and `update()`

### 2. Preprocessor (`preprocessor.py`)

**Purpose:** Image preprocessing (grayscale, background correction, thresholding)

**Key Methods:**
- `process(frame)` - Process single frame → binary mask

**Algorithm:**
1. Convert to grayscale
2. Background correction (static or high-pass)
3. Thresholding (Otsu or adaptive)
4. Morphological operations

**Extension:** Add new background correction methods:
```python
def _apply_custom_background(self, gray):
    # Your algorithm here
    return corrected
```

### 3. Segmenter (`segmenter.py`)

**Purpose:** Contour detection and filtering

**Key Methods:**
- `detect_contours(mask)` - Find and filter contours

**Filtering:**
- Area (min/max)
- Aspect ratio
- Spatial location (channel band)

**Extension:** Add custom filters:
```python
def _custom_filter(self, contour):
    # Your filter logic
    return True/False
```

### 4. Measurer (`measurer.py`)

**Purpose:** Calculate geometric metrics

**Key Methods:**
- `measure(contour)` - Calculate metrics → `DropletMetrics`

**Metrics:**
- Area, perimeter
- Major/minor axis (ellipse fitting)
- Equivalent diameter
- Centroid, bounding box

**Extension:** Add new metrics:
```python
# In DropletMetrics dataclass
new_metric: float

# In Measurer.measure()
metrics.new_metric = calculate_new_metric(contour)
```

### 5. ArtifactRejector (`artifact_rejector.py`)

**Purpose:** Filter static particles and artifacts

**Key Methods:**
- `filter(contours, prev_centroids)` - Temporal filtering

**Algorithm:**
- Motion validation (centroids must move downstream)
- Frame differencing (optional)

**Extension:** Add new rejection criteria:
```python
def _custom_rejection(self, contour, prev_centroids):
    # Your logic
    return True/False
```

### 6. DropletHistogram (`histogram.py`)

**Purpose:** Sliding-window statistics

**Key Methods:**
- `update(metrics)` - Add new measurements
- `get_histogram(metric)` - Get histogram data
- `get_statistics()` - Get statistics (mean, std, mode, etc.)

**Extension:** Add new metrics:
```python
# Add to __init__
self.new_metric_deque = deque(maxlen=window_size)

# Add to update()
self.new_metric_deque.append(metric.new_metric)

# Add to get_statistics()
stats['new_metric'] = calculate_stats(self.new_metric_deque)
```

### 7. DropletDetector (`detector.py`)

**Purpose:** Pipeline orchestrator

**Key Methods:**
- `process_frame(frame)` - Process frame → list of `DropletMetrics`

**Extension:** Add preprocessing/postprocessing:
```python
def process_frame(self, frame):
    # Custom preprocessing
    frame = self.custom_preprocess(frame)
    
    # Standard pipeline
    metrics = self._standard_pipeline(frame)
    
    # Custom postprocessing
    metrics = self.custom_postprocess(metrics)
    
    return metrics
```

---

## Extension Points

### 1. Adding a New Background Correction Method

**File:** `preprocessor.py`

```python
def _apply_background_correction(self, gray):
    if self.config.background_method == "static":
        return self._apply_static_background(gray)
    elif self.config.background_method == "highpass":
        return self._apply_highpass_background(gray)
    elif self.config.background_method == "custom":
        return self._apply_custom_background(gray)  # New method
    else:
        return gray

def _apply_custom_background(self, gray):
    # Your implementation
    pass
```

**Update config:**
```python
# In config.py, validate()
if self.background_method not in ["static", "highpass", "custom"]:
    errors.append(...)
```

### 2. Adding a New Thresholding Method

**File:** `preprocessor.py`

```python
def _apply_threshold(self, corrected):
    if self.config.threshold_method == "otsu":
        return self._apply_otsu_threshold(corrected)
    elif self.config.threshold_method == "adaptive":
        return self._apply_adaptive_threshold(corrected)
    elif self.config.threshold_method == "custom":
        return self._apply_custom_threshold(corrected)  # New method
    else:
        return self._apply_otsu_threshold(corrected)
```

### 3. Adding Custom Filtering

**File:** `segmenter.py`

```python
def detect_contours(self, mask, channel_band=None):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    filtered = []
    for contour in contours:
        if self._passes_area_filter(contour) and \
           self._passes_aspect_ratio_filter(contour) and \
           self._passes_spatial_filter(contour, channel_band) and \
           self._passes_custom_filter(contour):  # New filter
            filtered.append(contour)
    
    return filtered

def _passes_custom_filter(self, contour):
    # Your filter logic
    return True
```

### 4. Adding New Metrics

**File:** `measurer.py`

```python
@dataclass
class DropletMetrics:
    # Existing fields...
    new_metric: float  # Add new field

class Measurer:
    def measure(self, contour):
        metrics = DropletMetrics(...)
        
        # Existing calculations...
        metrics.new_metric = self._calculate_new_metric(contour)
        
        return metrics
    
    def _calculate_new_metric(self, contour):
        # Your calculation
        return value
```

**Update histogram:**
```python
# In histogram.py
def __init__(self, ...):
    # Existing deques...
    self.new_metric_deque = deque(maxlen=window_size)

def update(self, metrics):
    # Existing updates...
    self.new_metric_deque.append(metric.new_metric)
```

### 5. Adding a New Camera Backend

The system uses the existing camera abstraction (`BaseCamera`). To add support for a new camera:

1. **Create driver:** `drivers/camera/your_camera.py`
2. **Implement BaseCamera interface:**
   - `get_frame_roi(roi)` - Required for droplet detection
   - `start()`, `stop()`, `close()`
3. **Register in camera factory** (if needed)

The droplet detection system will automatically work with any camera that implements `get_frame_roi()`.

---

## Adding New Features

### Example: Adding Size Classification

**Step 1:** Add classification to `DropletMetrics`:

```python
@dataclass
class DropletMetrics:
    # Existing fields...
    size_category: str  # "small", "medium", "large"
```

**Step 2:** Implement classification in `Measurer`:

```python
def measure(self, contour):
    metrics = DropletMetrics(...)
    
    # Calculate area
    area = cv2.contourArea(contour)
    
    # Classify
    if area < 100:
        metrics.size_category = "small"
    elif area < 500:
        metrics.size_category = "medium"
    else:
        metrics.size_category = "large"
    
    return metrics
```

**Step 3:** Update histogram to track categories:

```python
# In histogram.py
def __init__(self, ...):
    self.size_category_counts = {'small': 0, 'medium': 0, 'large': 0}

def update(self, metrics):
    for metric in metrics:
        self.size_category_counts[metric.size_category] += 1
```

**Step 4:** Add to statistics output:

```python
def get_statistics(self):
    stats = {...}
    stats['size_distribution'] = dict(self.size_category_counts)
    return stats
```

### Example: Adding Export Functionality

**Create new module:** `droplet-detection/exporter.py`

```python
import json
from typing import List
from droplet_detection import DropletMetrics

class DropletExporter:
    def export_to_json(self, metrics: List[DropletMetrics], filename: str):
        data = [self._metric_to_dict(m) for m in metrics]
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _metric_to_dict(self, metric: DropletMetrics):
        return {
            'area': metric.area,
            'width': metric.major_axis,
            'height': metric.minor_axis,
            'diameter': metric.equivalent_diameter,
            # ... other fields
        }
```

**Integrate into controller:**

```python
# In droplet_detector_controller.py
from droplet_detection.exporter import DropletExporter

class DropletDetectorController:
    def __init__(self, ...):
        # ...
        self.exporter = DropletExporter()
    
    def export_frame(self, filename: str):
        # Get current frame metrics
        metrics = self.last_metrics
        self.exporter.export_to_json(metrics, filename)
```

---

## Testing

### Unit Tests

**Location:** `tests/test_droplet_detection.py`

**Run:**
```bash
python -m unittest discover -s tests -p "test_droplet_detection.py" -v
```

**Adding Tests:**
```python
class TestNewFeature(unittest.TestCase):
    def test_new_feature(self):
        # Your test
        pass
```

### Integration Tests

**Location:** `droplet-detection/test_integration.py`

**Run:**
```bash
python -m droplet_detection.test_integration
```

### Performance Tests

**Location:** `droplet-detection/benchmark.py`

**Run:**
```bash
python -m droplet_detection.benchmark
```

---

## Code Style

### Python Style

- Follow PEP 8
- Use type hints
- Document with docstrings
- Keep functions focused (single responsibility)

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `DropletDetector`)
- **Functions:** `snake_case` (e.g., `process_frame`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_AREA`)
- **Private methods:** `_leading_underscore` (e.g., `_apply_threshold`)

### Documentation

**Module docstring:**
```python
"""
Brief description.

Longer description if needed.
"""
```

**Class docstring:**
```python
class MyClass:
    """
    Brief description.
    
    Longer description.
    
    Attributes:
        attr1: Description
        attr2: Description
    """
```

**Method docstring:**
```python
def my_method(self, param1: int, param2: str) -> bool:
    """
    Brief description.
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Description
        
    Raises:
        ValueError: When condition
    """
```

### Error Handling

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Error message: {e}")
    # Handle error
    return None
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

---

## Best Practices

### 1. Keep Components Independent

Each component should work independently:
- No circular dependencies
- Clear interfaces
- Testable in isolation

### 2. Performance Considerations

- Use NumPy operations (vectorized)
- Avoid Python loops in hot paths
- Profile before optimizing
- Cache expensive calculations

### 3. Pi Compatibility

- Test on both 32-bit and 64-bit
- Avoid platform-specific code
- Use standard libraries
- Check memory usage

### 4. Configuration Management

- All tunable parameters in config
- Validate on load
- Provide sensible defaults
- Document parameter effects

### 5. Error Handling

- Validate inputs early
- Provide clear error messages
- Log errors for debugging
- Fail gracefully

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

```python
import cProfile

profiler = cProfile.Profile()
profiler.enable()

# Your code
result = detector.process_frame(frame)

profiler.disable()
profiler.print_stats()
```

### Visual Debugging

```python
import cv2

# Visualize intermediate results
cv2.imshow('mask', mask)
cv2.waitKey(0)

# Draw contours
debug_frame = frame.copy()
cv2.drawContours(debug_frame, contours, -1, (0, 255, 0), 2)
cv2.imshow('contours', debug_frame)
cv2.waitKey(0)
```

---

## Resources

- **Source Code:** `software/droplet-detection/`
- **Tests:** `software/tests/test_droplet_detection.py`
- **Documentation:** `docs/`
- **Roadmap:** `docs/droplet_detection_development_roadmap_v2.md`

---

**Last Updated:** December 2025
