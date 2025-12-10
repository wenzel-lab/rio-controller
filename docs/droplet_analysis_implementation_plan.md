# Droplet Analysis Implementation Plan
## Based on Requirements Analysis

**Date:** December 2025

---

## Current Implementation Status

### ✅ Already Implemented

1. **Basic Detection Pipeline**
   - Preprocessing, segmentation, measurement, artifact rejection
   - Real-time frame processing
   - Error handling and recovery

2. **Histogram System**
   - Sliding-window histogram using `deque(maxlen=2000)`
   - Real-time statistics (mean, std, min, max, mode)
   - Width, Height, Area, Diameter metrics
   - JSON serialization

3. **User Controls**
   - Start/Stop buttons in UI
   - WebSocket-based control (`droplet:start`, `droplet:stop`)
   - Reset functionality

4. **Calibration (Partial)**
   - `pixel_ratio` support (equivalent to `um_per_px`)
   - Unit conversion (px ↔ um)
   - **Issue:** Global setting, not per-camera

5. **Configuration System**
   - `DropletDetectionConfig` class
   - JSON serialization
   - Parameter profiles

6. **Real-time Updates**
   - Histogram updates every 2 seconds
   - Statistics updates
   - Status updates

---

## Missing Features (Requirements Gap Analysis)

### 🔴 High Priority

#### 1. Camera-Specific Calibration
**Status:** ❌ Not implemented  
**Requirement:** Each camera must have `um_per_px` in config  
**Current:** Global `pixel_ratio` in `DropletDetectionConfig`

**Implementation:**
- Add camera configuration structure
- Read `um_per_px` from camera config
- Pass camera-specific calibration to detector
- Update detector to use camera calibration

**Files to Modify:**
- `controllers/camera.py` - Add calibration storage
- `controllers/droplet_detector_controller.py` - Read from camera
- `droplet-detection/config.py` - Support camera-specific calibration

---

#### 2. Radius Offset Correction
**Status:** ❌ Not implemented  
**Requirement:** `radius_offset_px` per camera for threshold bias correction

**Implementation:**
- Add `radius_offset_px` to camera config
- Apply correction in `measurer.py`:
  ```python
  corrected_radius_px = detected_radius_px + radius_offset_px
  radius_um = corrected_radius_px * um_per_px
  ```
- Update all radius-based measurements

**Files to Modify:**
- `droplet-detection/measurer.py` - Apply offset correction
- `controllers/camera.py` - Store offset
- `droplet-detection/config.py` - Add offset parameter

---

#### 3. Pull-Based Processing (Skip Frames When Busy)
**Status:** ⚠️ Partially implemented  
**Current:** Processes all frames in queue (may cause backlog)  
**Requirement:** Skip intermediate frames, process only latest

**Implementation:**
- Modify `_processing_loop()` to:
  - Check if detector is busy
  - If busy, clear queue and get latest frame only
  - Process latest frame
- Add `processing_busy` flag

**Files to Modify:**
- `controllers/droplet_detector_controller.py` - Add frame skipping logic

---

#### 4. Processing Rate Display (Hz)
**Status:** ❌ Not implemented  
**Requirement:** Show "Processing rate: X.Y Hz" in UI

**Implementation:**
- Calculate FPS in processing loop
- Emit via WebSocket
- Display in UI

**Files to Modify:**
- `controllers/droplet_detector_controller.py` - Calculate FPS
- `rio-webapp/controllers/droplet_web_controller.py` - Emit FPS
- `rio-webapp/templates/index.html` - Display FPS
- `rio-webapp/static/droplet_histogram.js` - Update FPS display

---

#### 5. Module Enable/Disable
**Status:** ❌ Not implemented  
**Requirement:** `modules.droplet_analysis: true/false`

**Implementation:**
- Add module configuration check in `main.py`
- Only initialize droplet detection if enabled
- Hide UI panels if disabled

**Files to Modify:**
- `main.py` - Check module flag
- `rio-webapp/templates/index.html` - Conditional display

---

#### 6. Data Export (CSV/TXT)
**Status:** ❌ Not implemented  
**Requirement:** Export histogram data and raw measurements

**Implementation:**
- Add export endpoint: `GET /api/droplet/export?format=csv`
- Export raw droplet measurements with timestamps
- Include: timestamp_ms, radius_px, radius_um, area_px, area_um2, x_center_px, y_center_px, frame_id
- Use Python `csv` module (no heavy dependencies)

**Files to Create/Modify:**
- `rio-webapp/routes.py` - Add export endpoint
- `controllers/droplet_detector_controller.py` - Export method
- `rio-webapp/templates/index.html` - Export button
- `rio-webapp/static/droplet_histogram.js` - Export handler

---

### 🟡 Medium Priority

#### 7. Configurable Histogram Window Size
**Status:** ⚠️ Partially implemented  
**Current:** Hardcoded `maxlen=2000`  
**Requirement:** `histogram.window_size: 500` (configurable)

**Implementation:**
- Add `histogram_window_size` to config
- Use in `DropletHistogram` initialization
- Default to 500 if not specified

**Files to Modify:**
- `droplet-detection/config.py` - Add window_size
- `controllers/droplet_detector_controller.py` - Use config value

---

#### 8. REST API Endpoints
**Status:** ⚠️ Partially implemented  
**Current:** WebSocket only  
**Requirement:** `POST /droplets/start`, `POST /droplets/stop`

**Implementation:**
- Add REST endpoints alongside WebSocket
- Maintain backward compatibility

**Files to Modify:**
- `rio-webapp/routes.py` - Add REST endpoints

---

### 🟢 Low Priority / Nice to Have

#### 9. Configuration Structure Alignment
**Status:** ⚠️ Needs restructuring  
**Requirement:** Match specified structure:
```yaml
modules:
  droplet_analysis: true
cameras:
  cam1:
    um_per_px: 0.82
    radius_offset_px: -1.7
droplet_detection:
  threshold_method: "otsu"
  min_radius_um: 10
  max_radius_um: 120
histogram:
  window_size: 500
```

**Implementation:**
- Refactor config loading to support nested structure
- Maintain backward compatibility

---

## Implementation Plan (Phased Approach)

### Phase 1: Core Calibration & Processing (High Priority)

**Goal:** Enable accurate per-camera calibration and efficient processing

1. **Camera-Specific Calibration**
   - [ ] Add camera config structure
   - [ ] Read `um_per_px` from camera config
   - [ ] Pass to detector on initialization
   - [ ] Update histogram with camera calibration

2. **Radius Offset Correction**
   - [ ] Add `radius_offset_px` to camera config
   - [ ] Apply in `measurer.py`
   - [ ] Update all radius calculations
   - [ ] Test with known reference sizes

3. **Pull-Based Processing**
   - [ ] Add `processing_busy` flag
   - [ ] Modify queue handling to skip old frames
   - [ ] Process only latest frame when busy
   - [ ] Test performance on Raspberry Pi

**Estimated Time:** 2-3 days  
**Dependencies:** None

---

### Phase 2: UI Enhancements & Module Control (High Priority)

**Goal:** Improve user experience and enable module management

4. **Processing Rate Display**
   - [ ] Calculate FPS in processing loop
   - [ ] Emit via WebSocket
   - [ ] Display in UI
   - [ ] Update in real-time

5. **Module Enable/Disable**
   - [ ] Add module config check
   - [ ] Conditional initialization
   - [ ] Hide UI when disabled
   - [ ] Test enable/disable flow

**Estimated Time:** 1-2 days  
**Dependencies:** None

---

### Phase 3: Data Export (High Priority)

**Goal:** Enable data export for analysis

6. **CSV/TXT Export**
   - [ ] Store raw droplet measurements with timestamps
   - [ ] Add export endpoint
   - [ ] Implement CSV writer
   - [ ] Add export button to UI
   - [ ] Test export functionality

**Estimated Time:** 1-2 days  
**Dependencies:** Phase 1 (for accurate measurements)

---

### Phase 4: Configuration & API (Medium Priority)

**Goal:** Improve configuration management and API completeness

7. **Configurable Histogram Window**
   - [ ] Add to config
   - [ ] Use in histogram initialization
   - [ ] Test with different window sizes

8. **REST API Endpoints**
   - [ ] Add `POST /api/droplet/start`
   - [ ] Add `POST /api/droplet/stop`
   - [ ] Maintain WebSocket compatibility
   - [ ] Document endpoints

**Estimated Time:** 1 day  
**Dependencies:** None

---

### Phase 5: Configuration Restructuring (Low Priority)

**Goal:** Align with specified configuration structure

9. **Config Structure Alignment**
   - [ ] Refactor config loading
   - [ ] Support nested structure
   - [ ] Maintain backward compatibility
   - [ ] Update documentation

**Estimated Time:** 1-2 days  
**Dependencies:** All previous phases

---

## Detailed Implementation Notes

### 1. Camera-Specific Calibration

**Current Code:**
```python
# droplet_detector_controller.py
pixel_ratio = getattr(config, 'pixel_ratio', 1.0)
```

**Target Code:**
```python
# Get calibration from camera config
camera_config = self.camera.get_config()  # or similar
um_per_px = camera_config.get('um_per_px', 1.0)
pixel_ratio = um_per_px  # Use camera-specific value
```

**Changes Needed:**
- Add `get_config()` or `get_calibration()` to camera interface
- Store calibration in camera config file
- Read on detector initialization

---

### 2. Radius Offset Correction

**Implementation in `measurer.py`:**
```python
def measure(self, contours: List[np.ndarray], radius_offset_px: float = 0.0) -> List[DropletMetrics]:
    # ... existing measurement code ...
    
    # Apply radius offset correction
    corrected_radius_px = radius_px + radius_offset_px
    radius_um = corrected_radius_px * pixel_ratio
    
    # Update all radius-based metrics
```

**Changes Needed:**
- Add `radius_offset_px` parameter to `measure()`
- Get from camera config
- Apply to all radius calculations

---

### 3. Pull-Based Processing

**Current Code:**
```python
frame = self.frame_queue.get(timeout=0.1)
metrics = self._process_frame_with_timing(frame)
```

**Target Code:**
```python
# Skip old frames if busy
if self.processing_busy:
    # Clear queue and get latest
    while not self.frame_queue.empty():
        try:
            self.frame_queue.get_nowait()
        except queue.Empty:
            break
    try:
        frame = self.frame_queue.get_nowait()
    except queue.Empty:
        continue
else:
    frame = self.frame_queue.get(timeout=0.1)

self.processing_busy = True
try:
    metrics = self._process_frame_with_timing(frame)
finally:
    self.processing_busy = False
```

---

### 4. Processing Rate Display

**Implementation:**
```python
# In _processing_loop()
frames_processed = 0
rate_start_time = time.time()

# After processing frame
frames_processed += 1
if time.time() - rate_start_time >= 1.0:  # Update every second
    fps = frames_processed / (time.time() - rate_start_time)
    self.current_fps = fps
    frames_processed = 0
    rate_start_time = time.time()
```

**Emit via WebSocket:**
```python
# In droplet_web_controller.py
status = {
    "running": self.droplet_controller.running,
    "frame_count": self.droplet_controller.frame_count,
    "processing_rate_hz": self.droplet_controller.current_fps,
}
```

---

### 5. Data Export

**Store Raw Measurements:**
```python
# In droplet_detector_controller.py
self.raw_measurements: List[Dict] = []  # Store with timestamp

# After processing
for metric in metrics:
    self.raw_measurements.append({
        "timestamp_ms": int(time.time() * 1000),
        "frame_id": self.frame_count,
        "radius_px": metric.width / 2,  # or equivalent
        "radius_um": (metric.width / 2) * pixel_ratio,
        "area_px": metric.area,
        "area_um2": metric.area * (pixel_ratio ** 2),
        "x_center_px": metric.centroid[0],
        "y_center_px": metric.centroid[1],
    })
```

**Export Endpoint:**
```python
@routes.route('/api/droplet/export')
def export_droplet_data():
    format_type = request.args.get('format', 'csv')
    # Generate CSV or TXT
    # Return as download
```

---

## Testing Strategy

### Unit Tests
- Camera calibration reading
- Radius offset application
- Frame skipping logic
- FPS calculation
- Export format generation

### Integration Tests
- End-to-end calibration flow
- Processing with frame skipping
- Export functionality
- Module enable/disable

### Performance Tests
- Frame skipping effectiveness
- Processing rate accuracy
- Memory usage with large window sizes

---

## Documentation Updates

1. **User Guide**
   - Calibration procedure
   - Module enable/disable
   - Export functionality
   - Processing rate interpretation

2. **Developer Guide**
   - Configuration structure
   - Calibration system
   - Frame processing architecture
   - Export format specification

3. **API Documentation**
   - REST endpoints
   - WebSocket events
   - Configuration parameters

---

## Risk Assessment

### Low Risk
- Processing rate display
- Module enable/disable
- REST API endpoints

### Medium Risk
- Camera-specific calibration (requires camera config changes)
- Pull-based processing (may affect detection accuracy)

### High Risk
- Configuration restructuring (may break existing configs)
- Radius offset correction (requires validation)

---

## Success Criteria

### Phase 1 Complete When:
- ✅ Camera-specific `um_per_px` is read and applied
- ✅ Radius offset correction is applied correctly
- ✅ Frame skipping works without losing detection accuracy
- ✅ All tests pass

### Phase 2 Complete When:
- ✅ Processing rate is displayed and accurate
- ✅ Module can be enabled/disabled
- ✅ UI updates correctly based on module state

### Phase 3 Complete When:
- ✅ Export generates valid CSV/TXT files
- ✅ Export includes all required fields
- ✅ Export works from UI button

### All Phases Complete When:
- ✅ All requirements from specification are met
- ✅ All tests pass
- ✅ Documentation is updated
- ✅ Backward compatibility is maintained

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize phases** based on immediate needs
3. **Start with Phase 1** (Core Calibration & Processing)
4. **Iterate** based on feedback

---

**Last Updated:** December 2025
