# Software Design Roadmap: Strobe Rewrite + Droplet Detection Integration

**Branch:** `strobe-rewrite`  
**Target:** Raspberry Pi (32-bit & 64-bit), Camera V2 & HQ Camera, 20-90 FPS  
**Date:** Design roadmap for implementation

---

## 📋 EXECUTIVE SUMMARY

This roadmap outlines the integration of real-time droplet detection into the existing strobe-camera system, creating a unified platform-agnostic pipeline that works on both 32-bit and 64-bit Raspberry Pi OS.

**Key Goals:**
1. Complete strobe rewrite with hardware trigger support
2. Add fast droplet detection using classical CV (not YOLO)
3. Integrate histogram generation for real-time feedback
4. Maintain platform-agnostic architecture (32-bit & 64-bit)
5. Enable future closed-loop control based on droplet analysis

---

## 🔍 CURRENT STATE ANALYSIS

### What Exists (To Keep/Refactor)

#### ✅ **Strobe System** (`pistrobe.py`, `pistrobecam.py`)
- **Status:** Partially rewritten with hardware trigger support
- **Keep:**
  - SPI communication to PIC (`pistrobe.py`)
  - Hardware trigger mode (`set_trigger_mode()`)
  - GPIO trigger mechanism (`frame_callback_trigger()`)
- **Refactor:**
  - Simplify timing calculations (camera is master)
  - Better integration with droplet detection pipeline

#### ✅ **Camera System** (`camera_pi.py`, `pistrobecam.py`)
- **Status:** Working but needs enhancement
- **Keep:**
  - Thread-based frame capture
  - JPEG encoding for streaming
  - WebSocket integration
- **Refactor:**
  - Add ROI cropping support
  - Add raw numpy array output (for processing)
  - Abstract camera backend (32-bit vs 64-bit)

#### ✅ **Web Interface** (`pi_webapp.py`)
- **Status:** Functional Flask/SocketIO app
- **Keep:**
  - WebSocket communication
  - REST API endpoints
  - Real-time updates
- **Add:**
  - Droplet histogram visualization
  - Real-time droplet statistics
  - Detection parameters UI

### What's Missing (To Add)

#### ❌ **Droplet Detection Pipeline**
- **Status:** Not implemented
- **Add:**
  - Classical CV-based detection (OpenCV)
  - ROI cropping
  - Background subtraction
  - Contour detection & filtering
  - Motion-based tracking
  - Per-droplet metrics (size, length, area)

#### ❌ **Histogram Generation**
- **Status:** Not implemented
- **Add:**
  - Sliding-window histogram
  - Real-time statistics
  - JSON API endpoint
  - Web UI visualization

#### ❌ **Camera Abstraction Layer**
- **Status:** Hardcoded to `picamera` (32-bit)
- **Add:**
  - Base camera class
  - `PiCameraLegacy` (32-bit, `picamera`)
  - `PiCameraV2` (64-bit, `picamera2`)
  - Unified interface for both

#### ❌ **Frame Trigger Abstraction**
- **Status:** Not abstracted
- **Add:**
  - `FrameTrigger` base class
  - GPIO-based trigger (32-bit & 64-bit)
  - Hardware trigger support (if available)

### What to Eliminate/Simplify

#### 🗑️ **Complex Timing Calculations**
- **Current:** Complex frame rate calculations, dead time calculations
- **Simplify:** Camera is master, strobe follows (hardware trigger mode)
- **Eliminate:** Manual framerate optimization loops (keep simple)

#### 🗑️ **YOLO-Based Detection**
- **Current:** `droplet_AInalysis` uses YOLO (too slow for Pi)
- **Eliminate:** YOLO dependency for real-time detection
- **Keep:** YOLO as optional for post-processing/validation

#### 🗑️ **Full-Frame Processing**
- **Current:** Processes entire camera frame
- **Eliminate:** Full-frame processing (too slow)
- **Add:** ROI-only capture and processing

---

## 🏗️ ARCHITECTURE DESIGN

### 1. Camera Abstraction Layer

**Purpose:** Unified interface for 32-bit and 64-bit camera backends

**Design:**
```python
# camera_base.py
class BaseCamera:
    def start(self) -> None
    def stop(self) -> None
    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray
    def set_config(self, config: Dict) -> None
    def set_frame_callback(self, callback: Callable) -> None

class PiCameraLegacy(BaseCamera):  # 32-bit, picamera
    def __init__(self):
        self.cam = PiCamera()
    
    def get_frame_roi(self, roi):
        # Use camera.crop for ROI
        self.cam.crop = (roi[0], roi[1], roi[2], roi[3])
        return self.cam.capture_array()

class PiCameraV2(BaseCamera):  # 64-bit, picamera2
    def __init__(self):
        self.cam = Picamera2()
    
    def get_frame_roi(self, roi):
        # Capture full frame, crop in software
        request = self.cam.capture_array()
        return request[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
```

**Integration:**
- Replace direct `PiCamera` usage in `pistrobecam.py`
- Auto-detect OS and instantiate correct backend
- Processing code uses only `BaseCamera` interface

---

### 2. Frame Trigger Abstraction

**Purpose:** Unified trigger mechanism for both architectures

**Design:**
```python
# frame_trigger.py
class FrameTrigger:
    def wait_for_trigger(self) -> None
    def is_available(self) -> bool

class GPIOFrameTrigger(FrameTrigger):
    def __init__(self, gpio_pin: int):
        # GPIO-based trigger (software callback)
    
    def wait_for_trigger(self):
        # Wait for GPIO event or frame callback

class HardwareFrameTrigger(FrameTrigger):
    def __init__(self, gpio_pin: int):
        # Hardware trigger (XVS signal, if available)
    
    def wait_for_trigger(self):
        # Wait for hardware signal
```

**Integration:**
- Replace direct GPIO calls in `pistrobecam.py`
- Support both software and hardware triggers
- Fallback to fixed FPS if trigger unavailable

---

### 3. Droplet Detection Pipeline

**Purpose:** Fast, classical CV-based droplet detection

**Design:**
```python
# droplet_detection.py

class DropletDetector:
    def __init__(self, roi: Tuple, background_method: str = "temporal_median"):
        self.roi = roi
        self.background = None
        self.prev_centroids = []
    
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        # 1. Grayscale conversion
        # 2. Background subtraction (temporal median or static)
        # 3. High-pass filter (optional)
        # 4. Dynamic thresholding (Otsu or adaptive)
        return mask
    
    def detect_contours(self, mask: np.ndarray) -> List[Contour]:
        # 1. Find contours
        # 2. Filter by area (min/max)
        # 3. Filter by position (channel band)
        return filtered_contours
    
    def filter_moving_droplets(self, contours: List[Contour], 
                               prev_centroids: List[Tuple]) -> List[Contour]:
        # 1. Calculate centroids
        # 2. Compare to previous frame
        # 3. Filter by motion (monotonic downstream)
        # 4. Reject static artifacts
        return moving_droplets
    
    def measure_droplets(self, contours: List[Contour]) -> List[DropletMetrics]:
        # 1. Fit ellipse (major axis = length)
        # 2. Calculate area
        # 3. Calculate equivalent diameter
        return metrics
```

**Algorithm Details (from ADM paper & design brief):**

1. **Background Extraction:**
   - Object-based background extraction (ADM paper)
   - Temporal median filter (rolling window)
   - Static background at startup (fallback)

2. **Thresholding:**
   - Automated binary threshold value selection (ADM paper)
   - Otsu's method (fast, adaptive)
   - Adaptive threshold (for uneven lighting)

3. **Motion Filtering:**
   - Centroid-based tracking (thesis SI)
   - Monotonic downstream motion
   - Reject static artifacts

4. **Metrics:**
   - Major axis length (from fitted ellipse)
   - Area
   - Equivalent diameter
   - Centroid position (for tracking)

**Performance Targets:**
- Processing per frame: < 1-3 ms
- ROI height: 50-150 px
- Throughput: hundreds to thousands of droplets/second

---

### 4. Histogram Generation

**Purpose:** Real-time droplet size distribution

**Design:**
```python
# histogram.py
from collections import deque

class DropletHistogram:
    def __init__(self, maxlen: int = 2000, bins: int = 40):
        self.lengths = deque(maxlen=maxlen)
        self.areas = deque(maxlen=maxlen)
        self.bins = bins
    
    def update(self, droplet_metrics: List[DropletMetrics]):
        for metric in droplet_metrics:
            self.lengths.append(metric.length)
            self.areas.append(metric.area)
    
    def get_histogram(self, metric: str = "length", 
                     range: Tuple[float, float] = None) -> Tuple[np.ndarray, np.ndarray]:
        data = self.lengths if metric == "length" else self.areas
        return np.histogram(data, bins=self.bins, range=range)
    
    def get_statistics(self) -> Dict:
        return {
            "mean": np.mean(self.lengths),
            "std": np.std(self.lengths),
            "min": np.min(self.lengths),
            "max": np.max(self.lengths),
            "count": len(self.lengths)
        }
```

**Integration:**
- Update histogram after each frame
- Expose via JSON API endpoint
- Update web UI in real-time (2-10 Hz)

---

### 5. Unified Pipeline

**Purpose:** Integrate camera, strobe, and droplet detection

**Design:**
```python
# droplet_pipeline.py

class DropletPipeline:
    def __init__(self, camera: BaseCamera, strobe: PiStrobe, 
                 roi: Tuple, config: Dict):
        self.camera = camera
        self.strobe = strobe
        self.detector = DropletDetector(roi)
        self.histogram = DropletHistogram()
        self.trigger = FrameTrigger()
        self.config = config
    
    def run(self):
        # Thread 1: Camera capture + strobe trigger
        # Thread 2: Droplet detection + histogram update
        # Thread 3: Web UI updates (optional)
        
        self.camera.start()
        self.strobe.set_trigger_mode(True)
        self.strobe.set_enable(True)
        
        frame_queue = Queue(maxsize=2)  # Prevent memory buildup
        
        # Camera thread
        def capture_thread():
            while running:
                self.trigger.wait_for_trigger()
                frame = self.camera.get_frame_roi(self.detector.roi)
                frame_queue.put(frame, block=False)
        
        # Processing thread
        def process_thread():
            while running:
                try:
                    frame = frame_queue.get(timeout=0.1)
                    mask = self.detector.preprocess(frame)
                    contours = self.detector.detect_contours(mask)
                    moving = self.detector.filter_moving_droplets(contours, prev_centroids)
                    metrics = self.detector.measure_droplets(moving)
                    self.histogram.update(metrics)
                    prev_centroids = [m.centroid for m in metrics]
                except Empty:
                    continue
```

**Thread Architecture:**
- **Thread 1:** Camera capture + strobe trigger (I/O bound)
- **Thread 2:** Droplet detection (CPU bound)
- **Thread 3:** Web UI updates (low priority, 2-10 Hz)

**Synchronization:**
- `Queue` for frame transfer (maxsize=2 to prevent buildup)
- Lock-free where possible
- Event-based signaling for start/stop

---

## 📦 MODULE STRUCTURE

### New Files to Create

```
user-interface-software/src/
├── droplet_detection/
│   ├── __init__.py
│   ├── camera_base.py          # Camera abstraction layer
│   ├── frame_trigger.py        # Trigger abstraction
│   ├── droplet_detector.py     # Detection algorithm
│   ├── histogram.py            # Histogram generation
│   └── pipeline.py             # Unified pipeline
├── webapp/
│   ├── droplet_api.py          # REST API for droplet data
│   └── templates/
│       └── droplet_ui.html     # Histogram visualization
```

### Files to Modify

```
user-interface-software/src/webapp/
├── pistrobecam.py              # Refactor: use camera abstraction
├── camera_pi.py                # Add: droplet detection integration
└── pi_webapp.py                # Add: droplet API endpoints
```

### Files to Keep (Minimal Changes)

```
user-interface-software/src/webapp/
├── pistrobe.py                 # Keep: SPI communication
└── picommon.py                 # Keep: Common utilities
```

---

## 🔄 INTEGRATION STRATEGY

### Phase 1: Camera Abstraction (Week 1)
1. Create `camera_base.py` with `BaseCamera` interface
2. Implement `PiCameraLegacy` (32-bit)
3. Implement `PiCameraV2` (64-bit)
4. Test both backends independently
5. Update `pistrobecam.py` to use abstraction

### Phase 2: Droplet Detection Core (Week 1-2)
1. Implement `DropletDetector` class
2. Implement preprocessing pipeline
3. Implement contour detection & filtering
4. Implement motion-based filtering
5. Test with sample images/videos

### Phase 3: Histogram & Statistics (Week 2)
1. Implement `DropletHistogram` class
2. Add statistics calculation
3. Test histogram generation
4. Validate against known droplet sizes

### Phase 4: Pipeline Integration (Week 2-3)
1. Create `DropletPipeline` class
2. Integrate camera + detector + histogram
3. Implement threading architecture
4. Test end-to-end pipeline

### Phase 5: Web Interface (Week 3)
1. Add REST API endpoints for histogram
2. Create web UI for visualization
3. Add real-time updates via WebSocket
4. Test web interface

### Phase 6: Strobe Integration (Week 3-4)
1. Integrate strobe trigger with pipeline
2. Test hardware trigger mode
3. Optimize timing
4. Validate synchronization

### Phase 7: Testing & Optimization (Week 4)
1. Performance testing (20-90 FPS target)
2. Accuracy validation (compare to manual/DMV)
3. Memory optimization
4. Documentation

---

## 🎯 KEY DESIGN DECISIONS

### 1. Classical CV vs. YOLO
**Decision:** Use classical CV (OpenCV) for real-time detection  
**Rationale:**
- YOLO too slow for Pi (1-5 FPS)
- Classical CV achieves 20-90 FPS
- ADM paper shows ~300 FPS with OpenCV
- Sufficient for droplet size measurement

**Future:** YOLO/Coral TPU for classification (not detection)

### 2. ROI-Only Processing
**Decision:** Crop to ROI before processing  
**Rationale:**
- Reduces processing time by 10-100x
- IFC paper shows ROI-only capture
- Maintains full resolution for streaming
- Both cameras support ROI

### 3. Platform Abstraction
**Decision:** Abstract camera differences, keep processing identical  
**Rationale:**
- Single codebase for 32-bit & 64-bit
- Easier maintenance
- Consistent results across platforms
- Future-proof for new cameras

### 4. Threading Architecture
**Decision:** Separate threads for capture and processing  
**Rationale:**
- Prevents blocking camera I/O
- Allows parallel processing
- Better CPU utilization
- Matches ADM paper architecture

### 5. Motion-Based Filtering
**Decision:** Filter by centroid motion (monotonic downstream)  
**Rationale:**
- Rejects static artifacts (dirt)
- Lightweight (list of centroids)
- Thesis SI validates approach
- Pi-friendly computation

---

## 📊 PERFORMANCE TARGETS

### Processing Speed
- **Per-frame processing:** < 1-3 ms
- **Frame rate:** 20-90 FPS
- **Droplet throughput:** 100-1000 droplets/second
- **Histogram update:** 2-10 Hz

### Accuracy
- **Size measurement:** ±2% compared to manual/DMV
- **Detection rate:** >95% for droplets in focus
- **False positive rate:** <5% (filtered by motion)

### Resource Usage
- **CPU:** <50% on Raspberry Pi 4
- **Memory:** <200 MB for buffers
- **GPU:** Not required (CPU-only)

---

## 🔌 INTEGRATION WITH EXISTING CODE

### Strobe System
- **Keep:** `pistrobe.py` (SPI communication)
- **Modify:** `pistrobecam.py` (use camera abstraction, simplify timing)
- **Add:** Frame callback integration with droplet pipeline

### Web Interface
- **Keep:** Flask/SocketIO structure
- **Add:** Droplet API endpoints (`/api/droplet/histogram`, `/api/droplet/stats`)
- **Add:** Web UI for histogram visualization
- **Modify:** Camera streaming (add ROI overlay option)

### Flow Control (Future)
- **Prepare:** Histogram statistics as input to flow controller
- **Design:** Closed-loop control based on droplet size distribution
- **Interface:** REST API or WebSocket for control commands

---

## 📚 REFERENCES INTEGRATION

### ADM Paper (Chong et al., 2016)
**Key Techniques:**
- ✅ Object-based background extraction
- ✅ Automated binary threshold value selection
- ✅ OpenCV-based processing (~300 FPS)
- ✅ Camera SDK integration

**Implementation:**
- Use temporal median for background (object-based)
- Implement Otsu thresholding (automated)
- Use OpenCV for all processing
- Integrate with camera SDK (not VideoCapture)

### Embedded Blur-Free IFC Paper
**Key Techniques:**
- ✅ ROI-only capture
- ✅ Per-frame segmentation
- ✅ Simple morphology measurements
- ✅ Camera trigger-based processing

**Implementation:**
- Implement ROI cropping in camera abstraction
- Process each frame independently
- Measure major axis length (not complex shapes)
- Use camera trigger for frame alignment

### Thesis SI (Image-Based Droplet Length Control)
**Key Techniques:**
- ✅ Centroid-based filtering
- ✅ Monotonic downstream tracking
- ✅ Static artifact rejection

**Implementation:**
- Track centroids between frames
- Filter by motion direction
- Reject static contours

### YOLO-Based droplet_AInalysis
**Key Learnings:**
- ❌ Too slow for real-time on Pi
- ✅ Good for post-processing/validation
- ✅ Demonstrates droplet detection is possible
- ✅ Keep as reference, not for real-time

**Implementation:**
- Use classical CV for real-time
- Keep YOLO as optional validation tool
- Future: Coral TPU for YOLO if needed

---

## ⚠️ RISKS & MITIGATION

### Risk 1: Performance Not Meeting Targets
**Mitigation:**
- Start with ROI-only processing
- Optimize OpenCV operations (use efficient functions)
- Profile and optimize hot paths
- Fall back to lower FPS if needed

### Risk 2: Detection Accuracy Issues
**Mitigation:**
- Validate against manual measurements
- Compare to DMV software
- Tune threshold parameters
- Add calibration mode

### Risk 3: Platform Compatibility Issues
**Mitigation:**
- Test on both 32-bit and 64-bit early
- Use platform abstraction layer
- Keep processing code identical
- Document platform-specific quirks

### Risk 4: Memory Issues
**Mitigation:**
- Use bounded queues (maxsize=2)
- Limit histogram size (deque maxlen)
- Release frames promptly
- Monitor memory usage

---

## ✅ VALIDATION PLAN

### Unit Tests
- Camera abstraction (both backends)
- Droplet detection algorithm
- Histogram generation
- Motion filtering

### Integration Tests
- End-to-end pipeline
- Strobe synchronization
- Web interface
- Performance benchmarks

### Validation Tests
- Compare to manual measurements
- Compare to DMV software
- Test with known droplet sizes
- Test with different lighting conditions

---

## 📝 NEXT STEPS

1. **Review this roadmap** with team
2. **Create feature branch** from `strobe-rewrite`
3. **Start Phase 1:** Camera abstraction layer
4. **Iterate:** Build incrementally, test frequently
5. **Document:** Update as implementation progresses

---

## 🎓 LESSONS FROM REFERENCES

### ADM Paper
- Processing speed can exceed transfer speed
- Camera SDK integration is key
- Automated thresholding is essential
- OpenCV is fast enough for real-time

### IFC Paper
- ROI-only capture is critical
- Simple metrics are sufficient
- Camera trigger alignment helps
- Per-frame processing is feasible

### Thesis SI
- Motion filtering is lightweight and effective
- Centroid tracking is Pi-friendly
- Static artifact rejection is important
- Monotonic motion assumption is valid

---

**End of Roadmap**

**Questions or clarifications needed before implementation?**

