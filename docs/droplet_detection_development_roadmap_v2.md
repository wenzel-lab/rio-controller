# Droplet Detection Algorithm Development Roadmap v2.0
## Open Microfluidics Workstation - Strobe-Rewrite Branch

**Date:** December 2025  
**Repository:** open-microfluidics-workstation  
**Branch:** strobe-rewrite  
**Environment:** mamba rio-simulation  
**Status:** Ready for Implementation

---

## Executive Summary

This roadmap outlines the development of a **lightweight, real-time droplet detection algorithm** for the RIO modular microfluidics controller. The implementation will integrate seamlessly with the existing camera abstraction layer and strobe system.

**Key Features:**
- **Pi-compatible**: Works on Raspberry Pi OS 32-bit and 64-bit using existing camera abstraction
- **Lightweight**: Uses only OpenCV + NumPy (no heavy ML models)
- **Real-time**: Processes hundreds to low thousands of droplets per second
- **Integrated**: Leverages existing ROI support and camera infrastructure
- **Optimizable**: Parameter tuning tools using droplet_AInalysis dataset

**Design Principles:**
- Use `droplet_detection_design.txt` as a starting point and reference for algorithm concepts
- Generate our own implementation plan based on the design document, existing codebase, and requirements
- Use scientific papers (IFC, ADM) for conceptual inspiration only
- Maintain compatibility with existing camera abstraction layer
- Work exclusively in mamba rio-simulation environment
- Place all reports in `docs/` folder
- Assess and benchmark processing times for the entire pipeline (detection + histogram + statistics) to understand frame rate limits

---

## Current State Analysis

### ✅ What Already Exists (Leverage These)

#### 1. Camera Abstraction Layer (`drivers/camera/`)
**Status:** ✅ Complete and tested
- `BaseCamera` abstract base class with unified interface
- `PiCameraLegacy` (32-bit, picamera library)
- `PiCameraV2` (64-bit, picamera2 library)
- `MakoCamera` (Vimba SDK for external cameras)
- **ROI Support:** `get_frame_roi(roi: Tuple[int, int, int, int])` method already implemented
- **Frame Callbacks:** `set_frame_callback()` for strobe synchronization

**Integration Point:** Use `BaseCamera.get_frame_roi()` directly - no camera abstraction work needed!

#### 2. Strobe-Camera Integration (`controllers/strobe_cam.py`)
**Status:** ✅ Complete
- Hardware trigger mode via GPIO
- Frame callback integration
- `get_frame_roi()` method available via `PiStrobeCam.get_frame_roi()`

**Integration Point:** Access ROI frames through `strobe_cam.get_frame_roi(roi)`

#### 3. Camera Controller (`controllers/camera.py`)
**Status:** ✅ Complete
- ROI selection and storage (`self.roi` dictionary)
- WebSocket communication for ROI updates
- Frame streaming infrastructure

**Integration Point:** ROI coordinates available via `Camera.get_roi()` method

#### 4. Web Application Infrastructure (`rio-webapp/`)
**Status:** ✅ Complete
- Flask + SocketIO web framework
- REST API structure
- WebSocket event handlers
- Template system

**Integration Point:** Add droplet detection endpoints to existing webapp structure

### ❌ What Needs to Be Built

#### 1. Droplet Detection Pipeline (`software/droplet-detection/`)
**Status:** ❌ Empty directory - needs full implementation
- Preprocessing module (background correction, thresholding)
- Segmentation module (contour detection, filtering)
- Measurement module (geometric metrics)
- Artifact rejection (temporal filtering)

#### 2. Histogram & Statistics Module
**Status:** ❌ Not implemented
- Sliding-window histogram
- Real-time statistics calculation
- JSON serialization for API

#### 3. Parameter Optimization Tools
**Status:** ❌ Not implemented
- Dataset loader for droplet_AInalysis repository
- Parameter grid search
- Evaluation metrics
- Profile management (JSON)

#### 4. Web Integration
**Status:** ❌ Not implemented
- REST API endpoints for droplet data
- WebSocket events for real-time updates
- UI components for histogram visualization

---

## Architecture Design

### Module Structure

```
software/
├── droplet-detection/              # NEW: Droplet detection module
│   ├── __init__.py
│   ├── preprocessor.py            # Background correction, thresholding
│   ├── segmenter.py               # Contour detection, filtering
│   ├── measurer.py                # Geometric metrics calculation
│   ├── artifact_rejector.py      # Temporal filtering, motion validation
│   ├── detector.py                 # Main DropletDetector class (orchestrates modules)
│   ├── histogram.py               # Histogram and statistics
│   ├── config.py                  # Configuration and parameter profiles
│   └── utils.py                   # Helper functions
│
├── controllers/
│   ├── camera.py                  # ✅ EXISTS - ROI support available
│   ├── strobe_cam.py              # ✅ EXISTS - get_frame_roi() available
│   └── droplet_detector_controller.py  # NEW: Business logic for droplet detection
│
├── rio-webapp/
│   ├── controllers/
│   │   └── droplet_web_controller.py  # NEW: Web controller (HTTP/WebSocket)
│   └── routes.py                  # MODIFY: Add droplet routes
│
└── tests/
    └── test_droplet_detection.py  # NEW: Unit and integration tests
```

### Core Classes

#### 1. `DropletDetector` (Main Orchestrator)
```python
# software/droplet-detection/detector.py

class DropletDetector:
    """
    Main droplet detection orchestrator.
    
    Integrates preprocessing, segmentation, measurement, and artifact rejection.
    Designed to work with existing BaseCamera abstraction.
    """
    
    def __init__(self, roi: Tuple[int, int, int, int], config: Dict):
        self.roi = roi
        self.config = config
        self.preprocessor = Preprocessor(config)
        self.segmenter = Segmenter(config)
        self.measurer = Measurer(config)
        self.artifact_rejector = ArtifactRejector(config)
        self.prev_centroids = []
    
    def process_frame(self, frame: np.ndarray) -> List[DropletMetrics]:
        """
        Process a single ROI frame and return detected droplets.
        
        Args:
            frame: ROI frame from camera.get_frame_roi() (RGB numpy array)
            
        Returns:
            List of DropletMetrics objects
        """
        # 1. Preprocess
        mask = self.preprocessor.process(frame)
        
        # 2. Segment
        contours = self.segmenter.detect_contours(mask)
        
        # 3. Filter artifacts (temporal)
        moving_contours = self.artifact_rejector.filter(
            contours, self.prev_centroids
        )
        
        # 4. Measure
        metrics = self.measurer.measure(moving_contours)
        
        # 5. Update state
        self.prev_centroids = [m.centroid for m in metrics]
        
        return metrics
```

#### 2. `Preprocessor` (Background Correction & Thresholding)
```python
# software/droplet-detection/preprocessor.py

class Preprocessor:
    """
    Preprocessing module: background correction and thresholding.
    
    Implements:
    - Static background (median of N startup frames)
    - High-pass filtering (Gaussian blur subtraction)
    - Otsu thresholding
    - Adaptive thresholding (optional)
    """
    
    def process(self, frame: np.ndarray) -> np.ndarray:
        """Convert frame to binary mask."""
        # Grayscale conversion
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY) if len(frame.shape) == 3 else frame
        
        # Background correction
        if self.config['background_method'] == 'static':
            gray_corr = cv2.absdiff(gray, self.background)
        elif self.config['background_method'] == 'highpass':
            blur = cv2.GaussianBlur(gray, (11, 11), 0)
            gray_corr = cv2.subtract(gray, blur)
        
        # Thresholding
        if self.config['threshold_method'] == 'otsu':
            _, mask = cv2.threshold(gray_corr, 0, 255, 
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif self.config['threshold_method'] == 'adaptive':
            mask = cv2.adaptiveThreshold(gray_corr, 255, 
                                        cv2.ADAPTIVE_THRESH_MEAN_C, 
                                        cv2.THRESH_BINARY, 
                                        self.config['block_size'], 
                                        self.config['C'])
        
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                          self.config['morph_kernel'])
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
```

#### 3. `Segmenter` (Contour Detection & Filtering)
```python
# software/droplet-detection/segmenter.py

class Segmenter:
    """
    Segmentation module: contour detection and spatial filtering.
    
    Implements:
    - Contour extraction
    - Area-based filtering
    - Aspect ratio filtering
    - Spatial ROI filtering (within channel band)
    """
    
    def detect_contours(self, mask: np.ndarray) -> List[Contour]:
        """Extract and filter contours."""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, 
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        filtered = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = max(w, h) / max(1, min(w, h))
            
            # Filter by area
            if area < self.config['min_area'] or area > self.config['max_area']:
                continue
            
            # Filter by aspect ratio
            if aspect_ratio < self.config['min_aspect'] or \
               aspect_ratio > self.config['max_aspect']:
                continue
            
            filtered.append(cnt)
        
        return filtered
```

#### 4. `Measurer` (Geometric Metrics)
```python
# software/droplet-detection/measurer.py

class Measurer:
    """
    Measurement module: geometric metrics calculation.
    
    Implements:
    - Ellipse fitting (major axis = droplet length)
    - Equivalent diameter
    - Area calculation
    - Centroid calculation
    """
    
    def measure(self, contours: List[Contour]) -> List[DropletMetrics]:
        """Calculate metrics for each contour."""
        metrics = []
        for cnt in contours:
            # Fit ellipse
            if len(cnt) >= 5:
                ellipse = cv2.fitEllipse(cnt)
                major_axis = max(ellipse[1])
            else:
                # Fallback to bounding box
                x, y, w, h = cv2.boundingRect(cnt)
                major_axis = max(w, h)
            
            # Area
            area = cv2.contourArea(cnt)
            
            # Equivalent diameter
            eq_diameter = np.sqrt(4 * area / np.pi)
            
            # Centroid
            M = cv2.moments(cnt)
            cx = M["m10"] / (M["m00"] + 1e-5)
            cy = M["m01"] / (M["m00"] + 1e-5)
            
            metrics.append(DropletMetrics(
                area=area,
                major_axis=major_axis,
                equivalent_diameter=eq_diameter,
                centroid=(cx, cy),
                bounding_box=cv2.boundingRect(cnt)
            ))
        
        return metrics
```

#### 5. `ArtifactRejector` (Temporal Filtering)
```python
# software/droplet-detection/artifact_rejector.py

class ArtifactRejector:
    """
    Artifact rejection module: temporal filtering and motion validation.
    
    Implements:
    - Centroid-based tracking
    - Monotonic downstream motion validation
    - Static artifact rejection
    - Frame difference method (optional)
    """
    
    def filter(self, contours: List[Contour], 
               prev_centroids: List[Tuple[float, float]]) -> List[Contour]:
        """Filter contours by motion."""
        if not prev_centroids:
            return contours  # First frame, accept all
        
        moving_contours = []
        for cnt in contours:
            M = cv2.moments(cnt)
            cx = M["m10"] / (M["m00"] + 1e-5)
            cy = M["m01"] / (M["m00"] + 1e-5)
            
            # Check if centroid moved downstream (assuming flow direction)
            # Simple heuristic: check if moved right (x increased)
            is_moving = False
            for prev_cx, prev_cy in prev_centroids:
                dx = cx - prev_cx
                dy = abs(cy - prev_cy)
                
                # Movement in flow direction (right) and small perpendicular drift
                if dx > self.config['min_motion'] and dy < self.config['max_perp_drift']:
                    is_moving = True
                    break
            
            if is_moving or len(prev_centroids) == 0:
                moving_contours.append(cnt)
        
        return moving_contours
```

#### 6. `DropletHistogram` (Statistics)
```python
# software/droplet-detection/histogram.py

from collections import deque

class DropletHistogram:
    """
    Histogram and statistics module.
    
    Implements:
    - Sliding-window histogram (deque with maxlen)
    - Real-time statistics (mean, std, min, max, count)
    - JSON serialization
    """
    
    def __init__(self, maxlen: int = 2000, bins: int = 40):
        self.lengths = deque(maxlen=maxlen)
        self.areas = deque(maxlen=maxlen)
        self.equivalent_diameters = deque(maxlen=maxlen)
        self.bins = bins
    
    def update(self, metrics: List[DropletMetrics]):
        """Update histogram with new droplet measurements."""
        for m in metrics:
            self.lengths.append(m.major_axis)
            self.areas.append(m.area)
            self.equivalent_diameters.append(m.equivalent_diameter)
    
    def get_histogram(self, metric: str = "length", 
                     range: Optional[Tuple[float, float]] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Get histogram data."""
        data = getattr(self, f"{metric}s", self.lengths)
        return np.histogram(list(data), bins=self.bins, range=range)
    
    def get_statistics(self) -> Dict:
        """Get real-time statistics."""
        return {
            "count": len(self.lengths),
            "mean_length": np.mean(self.lengths) if self.lengths else 0,
            "std_length": np.std(self.lengths) if self.lengths else 0,
            "min_length": np.min(self.lengths) if self.lengths else 0,
            "max_length": np.max(self.lengths) if self.lengths else 0,
            "mean_area": np.mean(self.areas) if self.areas else 0,
            "mean_diameter": np.mean(self.equivalent_diameters) if self.equivalent_diameters else 0,
        }
    
    def to_json(self) -> Dict:
        """Serialize to JSON for API."""
        hist, bins = self.get_histogram("length")
        return {
            "histogram": {
                "counts": hist.tolist(),
                "bins": bins.tolist(),
            },
            "statistics": self.get_statistics(),
        }
```

---

## Development Phases

### Phase 1: Core Detection Pipeline (Week 1-2)

#### 1.1 Module Structure Setup
**Tasks:**
- [ ] Create `software/droplet-detection/` directory structure
- [ ] Create `__init__.py` with module exports
- [ ] Set up basic module skeleton files
- [ ] Add to `software/README.md` documentation

**Deliverables:**
- Module directory structure
- Basic imports and exports

#### 1.2 Preprocessing Module
**Tasks:**
- [ ] Implement `Preprocessor` class
- [ ] Implement grayscale conversion
- [ ] Implement static background method (median of N frames)
- [ ] Implement high-pass filtering method
- [ ] Implement Otsu thresholding
- [ ] Implement adaptive thresholding (optional)
- [ ] Implement morphological operations
- [ ] Write unit tests with sample images

**Deliverables:**
- `preprocessor.py` module
- Unit tests
- Performance benchmarks

#### 1.3 Segmentation Module
**Tasks:**
- [ ] Implement `Segmenter` class
- [ ] Implement contour extraction
- [ ] Implement area-based filtering
- [ ] Implement aspect ratio filtering
- [ ] Implement spatial ROI filtering (channel band)
- [ ] Write unit tests

**Deliverables:**
- `segmenter.py` module
- Unit tests

#### 1.4 Measurement Module
**Tasks:**
- [ ] Implement `Measurer` class
- [ ] Implement ellipse fitting
- [ ] Implement equivalent diameter calculation
- [ ] Implement centroid calculation
- [ ] Create `DropletMetrics` dataclass
- [ ] Write unit tests

**Deliverables:**
- `measurer.py` module
- `DropletMetrics` data structure
- Unit tests

#### 1.5 Artifact Rejection Module
**Tasks:**
- [ ] Implement `ArtifactRejector` class
- [ ] Implement centroid tracking
- [ ] Implement motion validation (monotonic downstream)
- [ ] Implement static artifact rejection
- [ ] Optional: Frame difference method
- [ ] Write unit tests

**Deliverables:**
- `artifact_rejector.py` module
- Unit tests

#### 1.6 Main Detector Integration
**Tasks:**
- [ ] Implement `DropletDetector` orchestrator class
- [ ] Integrate all modules
- [ ] Implement frame-by-frame processing
- [ ] Add error handling and logging
- [ ] Write integration tests

**Deliverables:**
- `detector.py` module
- Integration tests
- Performance profiling

---

### Phase 2: Histogram & Statistics (Week 2-3)

#### 2.1 Histogram Module
**Tasks:**
- [ ] Implement `DropletHistogram` class
- [ ] Implement sliding-window deque storage
- [ ] Implement histogram calculation
- [ ] Implement statistics calculation
- [ ] Implement JSON serialization
- [ ] Write unit tests

**Deliverables:**
- `histogram.py` module
- Unit tests

#### 2.2 Configuration System
**Tasks:**
- [ ] Design JSON schema for parameter profiles
- [ ] Implement `Config` class for parameter management
- [ ] Create default parameter profiles
- [ ] Implement profile save/load functionality
- [ ] Add validation for parameter ranges

**Deliverables:**
- `config.py` module
- Example parameter profiles
- Profile management API

---

### Phase 3: Controller Integration (Week 3-4)

#### 3.1 Droplet Detector Controller (Business Logic)
**Tasks:**
- [ ] Create `controllers/droplet_detector_controller.py`
- [ ] Integrate with existing `Camera` controller
- [ ] Integrate with `PiStrobeCam` for ROI frames
- [ ] Implement thread-safe processing pipeline
- [ ] Add start/stop functionality
- [ ] Add configuration management
- [ ] Implement processing time benchmarking and monitoring

**Deliverables:**
- `droplet_detector_controller.py`
- Integration with existing camera system
- Threading architecture
- Performance monitoring tools

#### 3.2 Real-Time Processing Pipeline
**Tasks:**
- [ ] Design threading architecture:
  - Thread 1: Camera capture (existing)
  - Thread 2: Droplet detection processing
  - Thread 3: Histogram updates
- [ ] Implement frame queue (bounded, maxsize=2)
- [ ] Implement processing loop
- [ ] Add frame dropping strategy for overload
- [ ] Add comprehensive timing instrumentation:
  - Per-frame processing time (detection pipeline)
  - Histogram update time
  - Statistics calculation time
  - Total pipeline latency
  - Frame rate capability assessment
- [ ] Create performance profiling tools
- [ ] Document frame rate limits based on measured processing times

**Deliverables:**
- Multi-threaded processing pipeline
- Performance benchmarks with detailed timing breakdown
- Latency measurements
- Frame rate limit documentation

---

### Phase 4: Web Integration (Week 4-5)

#### 4.1 REST API Endpoints
**Tasks:**
- [ ] Add routes to `rio-webapp/routes.py`:
  - `GET /api/droplet/status` - Get detection status
  - `POST /api/droplet/start` - Start detection
  - `POST /api/droplet/stop` - Stop detection
  - `GET /api/droplet/histogram` - Get histogram data
  - `GET /api/droplet/statistics` - Get statistics
  - `POST /api/droplet/config` - Update configuration
  - `POST /api/droplet/profile` - Load parameter profile
- [ ] Implement error handling
- [ ] Add API documentation

**Deliverables:**
- REST API endpoints
- API documentation

#### 4.2 WebSocket Integration
**Tasks:**
- [ ] Add WebSocket events to `rio-webapp/controllers/droplet_web_controller.py`:
  - `droplet:histogram` - Real-time histogram updates
  - `droplet:statistics` - Real-time statistics updates
  - `droplet:detection` - Individual droplet detections (optional)
  - `droplet:performance` - Processing time metrics (optional, for debugging)
- [ ] Implement event emission
- [ ] Add rate limiting (2-10 Hz updates)

**Deliverables:**
- WebSocket event handlers
- Real-time updates

#### 4.3 Web UI Components
**Tasks:**
- [ ] Create histogram visualization component (JavaScript)
- [ ] Add to existing web interface
- [ ] Create statistics display
- [ ] Add configuration UI (parameter adjustment)
- [ ] Add profile selection UI

**Deliverables:**
- Web UI components
- Integration with existing interface

---

### Phase 5: Parameter Optimization Tools (Week 5-6)

#### 5.1 Dataset Integration
**Tasks:**
- [ ] Create dataset loader for `droplet_AInalysis` repository
- [ ] Implement image/video loading
- [ ] Implement ground truth extraction (if available)
- [ ] Create validation dataset structure

**Deliverables:**
- Dataset loader utilities
- Ground truth format specification

#### 5.2 Parameter Optimization Framework
**Tasks:**
- [ ] Implement parameter grid search
- [ ] Implement evaluation metrics:
  - Detection rate
  - False positive rate
  - False negative rate
  - Size measurement error (if ground truth available)
- [ ] Create optimization script (offline, on PC)
- [ ] Add SciPy optimization support (optional)

**Deliverables:**
- Parameter optimization tools
- Evaluation metrics
- Optimization scripts

#### 5.3 Profile Management
**Tasks:**
- [ ] Create parameter profiles for different:
  - Chip types
  - Reagent combinations
  - Illumination settings
- [ ] Implement profile validation
- [ ] Add profile documentation

**Deliverables:**
- Parameter profile library
- Profile documentation

---

### Phase 6: Performance Assessment & Benchmarking (Week 6)

#### 6.1 Processing Time Analysis
**Tasks:**
- [ ] Implement comprehensive timing instrumentation:
  - Preprocessing time (background correction + thresholding)
  - Segmentation time (contour detection + filtering)
  - Measurement time (geometric metrics calculation)
  - Artifact rejection time (temporal filtering)
  - Histogram update time
  - Statistics calculation time
  - Total per-frame processing time
- [ ] Create benchmarking script
- [ ] Test with various ROI sizes:
  - Small ROI: 50×256 px
  - Medium ROI: 100×512 px
  - Large ROI: 150×1024 px
- [ ] Test with various droplet densities:
  - Low density: 1-5 droplets/frame
  - Medium density: 5-20 droplets/frame
  - High density: 20+ droplets/frame
- [ ] Measure on both Pi32 and Pi64
- [ ] Document frame rate limits based on measured times
- [ ] Create performance report in `docs/`

**Deliverables:**
- Timing instrumentation code
- Benchmarking scripts
- Performance report with frame rate limits
- Recommendations for optimal ROI sizes and frame rates

#### 6.2 Frame Rate Limit Assessment
**Tasks:**
- [ ] Calculate maximum sustainable frame rate:
  - Based on measured processing times
  - Account for camera capture overhead
  - Account for histogram/statistics overhead
  - Account for WebSocket update overhead
- [ ] Determine optimal frame dropping strategy
- [ ] Test under sustained load
- [ ] Document performance characteristics

**Deliverables:**
- Frame rate limit documentation
- Performance characteristics report

### Phase 7: Testing & Validation (Week 7-8)

#### 7.1 Unit Testing
**Tasks:**
- [ ] Write unit tests for all modules:
  - Preprocessor
  - Segmenter
  - Measurer
  - ArtifactRejector
  - Histogram
- [ ] Create test fixtures with sample images
- [ ] Achieve >80% code coverage

**Deliverables:**
- Complete unit test suite
- Test coverage report

#### 7.2 Integration Testing
**Tasks:**
- [ ] Test full pipeline with real camera feeds
- [ ] Test on both Pi32 and Pi64
- [ ] Validate ROI functionality
- [ ] Test parameter profile loading
- [ ] Performance testing under various conditions

**Deliverables:**
- Integration test results
- Cross-platform compatibility report
- Performance benchmarks

#### 7.3 Validation Against droplet_AInalysis
**Tasks:**
- [ ] Run detection on droplet_AInalysis test images
- [ ] Compare results with YOLO predictions (qualitative)
- [ ] Measure detection accuracy
- [ ] Document differences and trade-offs

**Deliverables:**
- Validation report in `docs/`
- Comparison analysis
- Accuracy metrics

---

### Phase 8: Documentation & Deployment (Week 8-9)

#### 8.1 Code Documentation
**Tasks:**
- [ ] Add comprehensive docstrings to all classes and methods
- [ ] Document algorithm choices and trade-offs
- [ ] Create architecture diagrams
- [ ] Document parameter tuning guide

**Deliverables:**
- Complete code documentation
- Architecture documentation

#### 8.2 User Documentation
**Tasks:**
- [ ] Create user guide in `docs/`:
  - Installation instructions (mamba environment)
  - Configuration guide
  - Parameter tuning guide
  - Troubleshooting
- [ ] Create developer guide:
  - Module structure
  - Extension points
  - Adding new camera backends
- [ ] Update main README with droplet detection information

**Deliverables:**
- User documentation
- Developer documentation
- Updated README

#### 8.3 Deployment Preparation
**Tasks:**
- [ ] Create deployment checklist
- [ ] Test on clean Pi installation
- [ ] Create installation script (if needed)
- [ ] Document environment setup

**Deliverables:**
- Deployment guide
- Installation verification

---

## Integration with Existing Code

### Camera System Integration

**Existing Code:**
```python
# controllers/camera.py
class Camera:
    def get_roi(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current ROI coordinates."""
        if self.roi:
            return (self.roi["x"], self.roi["y"], 
                   self.roi["width"], self.roi["height"])
        return None
```

**Integration:**
```python
# controllers/droplet_detector_controller.py
class DropletDetectorController:
    def __init__(self, camera: Camera, strobe_cam: PiStrobeCam):
        self.camera = camera
        self.strobe_cam = strobe_cam
        self.detector = None
        self.histogram = DropletHistogram()
    
    def start(self):
        roi = self.camera.get_roi()
        if roi is None:
            raise ValueError("ROI not set")
        
        config = self.load_config()
        self.detector = DropletDetector(roi, config)
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_loop)
        self.processing_thread.start()
    
    def _process_loop(self):
        while self.running:
            roi = self.camera.get_roi()
            if roi:
                frame = self.strobe_cam.get_frame_roi(roi)
                metrics = self.detector.process_frame(frame)
                self.histogram.update(metrics)
```

### Strobe System Integration

**Existing Code:**
```python
# controllers/strobe_cam.py
class PiStrobeCam:
    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Get ROI frame for droplet detection."""
        return self.camera.get_frame_roi(roi)
```

**Integration:** Already compatible! Use `strobe_cam.get_frame_roi()` directly.

### Web Application Integration

**Existing Code:**
```python
# rio-webapp/routes.py
@app.route('/api/camera/...')
def camera_endpoint():
    ...
```

**Integration:**
```python
# rio-webapp/routes.py
from controllers.droplet_detector_controller import DropletDetectorController

droplet_ctrl = DropletDetectorController(camera, strobe_cam)

@app.route('/api/droplet/histogram')
def get_histogram():
    return jsonify(droplet_ctrl.histogram.to_json())
```

---

## Algorithm Details (Informed by Design Documents)

**Note:** The following algorithm details are informed by `droplet_detection_design.txt` and scientific papers, but represent our own implementation plan tailored to the existing codebase and requirements.

### Preprocessing Pipeline
1. **Grayscale Conversion**: `cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)`
2. **Background Correction**:
   - Option 1: Static background (median of N startup frames)
   - Option 2: High-pass filtering (Gaussian blur subtraction)
3. **Thresholding**:
   - Otsu threshold (global, automatic)
   - Adaptive threshold (local, for uneven lighting)
4. **Morphological Cleanup**:
   - Opening (noise removal)
   - Closing (hole filling, optional)

### Segmentation Pipeline
1. **Contour Extraction**: `cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`
2. **Area Filtering**: Reject contours outside min/max area bounds
3. **Aspect Ratio Filtering**: Reject contours with unrealistic aspect ratios
4. **Spatial Filtering**: Ensure contours are within channel ROI band

### Measurement Pipeline
1. **Ellipse Fitting**: `cv2.fitEllipse(cnt)` → major axis = droplet length
2. **Area Calculation**: `cv2.contourArea(cnt)`
3. **Equivalent Diameter**: `sqrt(4 * area / π)`
4. **Centroid**: Moments-based calculation

### Artifact Rejection Pipeline
1. **Centroid Tracking**: Maintain list of previous frame centroids
2. **Motion Validation**: Check if centroid moved downstream (monotonic)
3. **Static Rejection**: Reject contours that haven't moved
4. **Frame Difference** (optional): `cv2.absdiff()` for change detection

---

## Processing Time Assessment & Frame Rate Limits

### Critical Performance Metrics

Understanding the processing time for each component is essential to determine:
1. **Maximum sustainable frame rate** - How fast can we process frames?
2. **Frame dropping strategy** - When to skip frames if processing can't keep up
3. **ROI size limits** - What ROI sizes are feasible for real-time processing?
4. **Droplet density limits** - How many droplets per frame can we handle?

### Timing Instrumentation Requirements

Each component must be instrumented with timing measurements:

```python
# Example timing instrumentation
import time

class TimingInstrumentation:
    def __init__(self):
        self.timings = {
            'preprocessing': [],
            'segmentation': [],
            'measurement': [],
            'artifact_rejection': [],
            'histogram_update': [],
            'statistics_calc': [],
            'total_per_frame': []
        }
    
    def time_preprocessing(self, func):
        start = time.perf_counter()
        result = func()
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        self.timings['preprocessing'].append(elapsed)
        return result
    
    def get_statistics(self) -> Dict:
        """Get timing statistics for each component."""
        stats = {}
        for component, times in self.timings.items():
            if times:
                stats[component] = {
                    'mean': np.mean(times),
                    'std': np.std(times),
                    'min': np.min(times),
                    'max': np.max(times),
                    'p95': np.percentile(times, 95),
                    'p99': np.percentile(times, 99),
                }
        return stats
```

### Benchmarking Scenarios

**Phase 6.1** will include comprehensive benchmarking:

1. **ROI Size Variations:**
   - Small: 50×256 px (~12,800 pixels)
   - Medium: 100×512 px (~51,200 pixels)
   - Large: 150×1024 px (~153,600 pixels)

2. **Droplet Density Variations:**
   - Low: 1-5 droplets/frame
   - Medium: 5-20 droplets/frame
   - High: 20+ droplets/frame

3. **Platform Variations:**
   - Raspberry Pi 4 (32-bit)
   - Raspberry Pi 4 (64-bit)
   - Simulation mode (for development)

4. **Component Breakdown:**
   - Measure each processing step independently
   - Measure histogram update time separately
   - Measure statistics calculation time separately
   - Measure total pipeline time

### Frame Rate Limit Calculation

Based on measured processing times:

```
Maximum Frame Rate = 1000 ms / (Total Processing Time + Safety Margin)

Where:
- Total Processing Time = preprocessing + segmentation + measurement + 
                          artifact_rejection + histogram_update + statistics_calc
- Safety Margin = 10-20% buffer for system overhead
```

### Performance Monitoring

Real-time performance monitoring will be available via:
- WebSocket events (optional, for debugging)
- Logging (configurable verbosity)
- API endpoint: `GET /api/droplet/performance` (returns timing statistics)

---

## Performance Targets

### Processing Speed (To Be Validated Through Benchmarking)
**Note:** These are initial targets. Actual performance will be measured and documented in Phase 6.

- **Per-frame processing**: < 1-3 ms (for ROI ~50-150 px height × 256-1024 px width)
  - Preprocessing: < 0.5-1 ms
  - Segmentation: < 0.5-1 ms
  - Measurement: < 0.2-0.5 ms
  - Artifact rejection: < 0.2-0.5 ms
- **Histogram update**: < 0.1-0.2 ms
- **Statistics calculation**: < 0.1 ms
- **Total pipeline**: < 1.5-3.5 ms per frame
- **Frame rate capability**: To be determined through benchmarking (target: 100+ FPS on Pi 4)
- **Droplet throughput**: 100-1000 droplets/second (dependent on frame rate and droplet density)
- **Histogram update rate**: 2-10 Hz (WebSocket, separate from processing)

### Accuracy
- **Detection rate**: >95% for droplets in focus
- **False positive rate**: <5% (after artifact rejection)
- **Size measurement**: ±2% compared to manual measurements (if ground truth available)

### Resource Usage
- **CPU**: <50% on Raspberry Pi 4
- **Memory**: <200 MB for buffers and histogram
- **GPU**: Not required (CPU-only)

---

## Parameter Ranges (Initial Estimates)

Based on design documents and typical microfluidic droplet sizes:

- **Background frames**: 10-50 frames for static background
- **Gaussian blur kernel**: (11, 11) for high-pass filtering
- **Morphological kernel**: (3, 3) to (5, 5) ellipse
- **Min area**: 10-50 pixels² (chip-dependent)
- **Max area**: 1000-10000 pixels² (chip-dependent)
- **Aspect ratio bounds**: 1.5-10 (droplet-dependent)
- **Min motion**: 2-5 pixels (frame-to-frame)
- **Max perpendicular drift**: 5-10 pixels

These will be optimized using the parameter optimization tools.

---

## Risk Mitigation

### Technical Risks

1. **Performance on Pi32**: May need further optimization
   - *Mitigation*: Early benchmarking, profile-guided optimization, ROI-only processing

2. **ROI configuration complexity**: Different cameras handle ROI differently
   - *Mitigation*: Camera abstraction already handles this - use `get_frame_roi()` directly

3. **Parameter sensitivity**: Algorithm may be sensitive to illumination changes
   - *Mitigation*: Robust parameter optimization, adaptive background updates, multiple threshold methods

### Schedule Risks

1. **Optimization takes longer than expected**
   - *Mitigation*: Prioritize core functionality, optimize incrementally, use existing camera infrastructure

2. **Integration complexity with existing webapp**
   - *Mitigation*: Early API design, incremental integration, leverage existing Flask/SocketIO structure

---

## Success Criteria

### Functional Requirements
- [ ] Detects droplets in real-time on Pi32 and Pi64
- [ ] Processes 100+ FPS on Pi 4 with small ROI
- [ ] Rejects static artifacts and dirt
- [ ] Provides accurate size measurements
- [ ] Generates histograms and statistics
- [ ] Supports parameter profile management
- [ ] Integrates with existing camera and strobe systems

### Performance Requirements
- [ ] <10 ms processing latency per frame
- [ ] <200 MB memory footprint
- [ ] >95% detection rate on test dataset
- [ ] <5% false positive rate

### Quality Requirements
- [ ] >80% code coverage
- [ ] Comprehensive documentation
- [ ] Cross-platform compatibility (Pi32/Pi64)
- [ ] Clean, modular architecture

---

## References

### Design Documents (Starting Point & Reference)
- `cursor_roadmap_and_source_use.txt` - Development principles and source usage guidelines
- `droplet_detection_design.txt` - Algorithm concepts and design suggestions (used as reference, not authoritative)

### Scientific Papers (Conceptual Reference Only)
- **Embedded Blur-Free IFC Paper**: ROI-based acquisition, contour segmentation concepts
- **ADM Paper**: Geometric metrics, temporal smoothing, artifact rejection concepts

### Related Repositories
- `droplet_AInalysis` - Dataset and reference implementation (YOLO-based, for validation)
- `flow-microscopy-platform` - Related hardware/firmware (for reference)

---

## Environment & Repository Management

### Development Environment
- **Environment**: mamba rio-simulation
- **Activation**: `mamba activate rio-simulation`
- **Location**: All development in `software/` directory
- **Never install to system root**: Always use mamba environment

### Documentation Location
- **Reports**: All reports go in `docs/` folder
- **Code documentation**: Inline docstrings + `docs/` for architecture
- **User guides**: `docs/` folder

### Testing
- **Unit tests**: `software/tests/test_droplet_detection.py`
- **Integration tests**: Include in `test_integration.py`
- **Run tests**: In mamba environment: `python tests/test_droplet_detection.py`

---

## Next Steps

1. **Review this roadmap** with team
2. **Confirm Phase 1 start date**
3. **Set up development environment**: `mamba activate rio-simulation`
4. **Create feature branch**: `git checkout -b droplet-detection-phase1`
5. **Start Phase 1.1**: Module structure setup
6. **Iterate**: Build incrementally, test frequently, document as you go

---

**Document Version**: 2.1  
**Last Updated**: December 2025  
**Next Review**: After Phase 1 completion  
**Status**: Ready for Implementation
