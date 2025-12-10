# Droplet Analysis Phase 1 Implementation
## Core Calibration & Processing

**Date:** December 2025

---

## Overview

Phase 1 implements the core calibration and processing improvements:
1. Camera-specific calibration (um_per_px per camera)
2. Radius offset correction for threshold bias
3. Pull-based processing (skip frames when busy)

---

## Implementation Details

### 1. Camera-Specific Calibration

**Changes Made:**

#### `controllers/camera.py`
- Added `calibration` dictionary to store `um_per_px` and `radius_offset_px`
- Added `get_calibration()` method to retrieve calibration
- Added `set_calibration()` method to update calibration

```python
# Camera calibration for droplet detection
self.calibration: Dict[str, float] = {
    "um_per_px": 1.0,  # Default: 1 um per pixel
    "radius_offset_px": 0.0,  # Default: no offset
}

def get_calibration(self) -> Dict[str, float]:
    """Get camera calibration parameters."""
    return self.calibration.copy()

def set_calibration(self, um_per_px: Optional[float] = None, 
                    radius_offset_px: Optional[float] = None) -> None:
    """Set camera calibration parameters."""
    # Updates calibration values
```

#### `controllers/droplet_detector_controller.py`
- Modified initialization to read calibration from camera
- Falls back to config `pixel_ratio` if camera calibration not available
- Stores `um_per_px` and `radius_offset_px` as instance variables
- Updates histogram with camera-specific calibration

```python
# Get calibration from camera (camera-specific) or fallback to config
camera_calibration = camera.get_calibration() if hasattr(camera, 'get_calibration') else {}
um_per_px = camera_calibration.get('um_per_px', getattr(self.config, 'pixel_ratio', 1.0))
self.radius_offset_px = camera_calibration.get('radius_offset_px', 0.0)

self.um_per_px = um_per_px
self.histogram = DropletHistogram(maxlen=2000, bins=40, pixel_ratio=um_per_px, unit=unit)
```

**Benefits:**
- Each camera can have its own calibration
- Calibration persists with camera instance
- Backward compatible with global `pixel_ratio` config

---

### 2. Radius Offset Correction

**Changes Made:**

#### `droplet-detection/measurer.py`
- Added `radius_offset_px` parameter to `measure()` method
- Applies offset correction to both `equivalent_diameter` and `major_axis`
- Ensures corrected radius is non-negative

```python
def measure(self, contours: List[np.ndarray], radius_offset_px: float = 0.0) -> List[DropletMetrics]:
    # ... existing measurement code ...
    
    # Apply radius offset correction for threshold bias
    radius_raw = equivalent_diameter_raw / 2.0
    corrected_radius = max(0.0, radius_raw + radius_offset_px)
    equivalent_diameter = corrected_radius * 2.0
    
    # Also apply to major_axis
    major_axis_radius = major_axis / 2.0
    corrected_major_radius = max(0.0, major_axis_radius + radius_offset_px)
    major_axis = corrected_major_radius * 2.0
```

#### `droplet-detection/detector.py`
- Added `radius_offset_px` parameter to `__init__()`
- Passes offset to `measurer.measure()`

```python
def __init__(self, roi: Tuple[int, int, int, int], 
             config: Optional[DropletDetectionConfig] = None,
             radius_offset_px: float = 0.0):
    self.radius_offset_px = radius_offset_px
    # ...

metrics = self.measurer.measure(moving_contours, radius_offset_px=self.radius_offset_px)
```

#### `controllers/droplet_detector_controller.py`
- Passes `radius_offset_px` when creating detector
- Updates detector when offset changes via config

```python
self.detector = DropletDetector(roi, self.config, radius_offset_px=self.radius_offset_px)
```

**Benefits:**
- Corrects for systematic threshold bias
- Per-camera offset support
- Applied to all radius-based measurements

---

### 3. Pull-Based Processing

**Changes Made:**

#### `controllers/droplet_detector_controller.py`
- Added `processing_busy` flag to track processing state
- Modified `_processing_loop()` to skip old frames when busy
- Only processes latest frame when backlog occurs

```python
self.processing_busy = False  # Flag to indicate if processing is currently busy

# In _processing_loop():
if self.processing_busy:
    # Clear queue and get only the latest frame
    latest_frame = None
    while not self.frame_queue.empty():
        try:
            latest_frame = self.frame_queue.get_nowait()
        except queue.Empty:
            break
    
    if latest_frame is None:
        time.sleep(0.01)
        continue
    frame = latest_frame
else:
    # Normal processing: get frame from queue
    frame = self.frame_queue.get(timeout=0.1)

# Mark as busy and process
self.processing_busy = True
try:
    metrics = self._process_frame_with_timing(frame)
finally:
    self.processing_busy = False
```

**Benefits:**
- Prevents frame backlog on Raspberry Pi
- Always processes most recent frame
- Maintains real-time performance
- Reduces memory usage

---

## Configuration Updates

### Setting Camera Calibration

**Via Code:**
```python
camera.set_calibration(um_per_px=0.82, radius_offset_px=-1.7)
```

**Via Config Update:**
```python
# Update via droplet detector controller
controller.update_config({
    'um_per_px': 0.82,
    'radius_offset_px': -1.7
})
```

**Default Values:**
- `um_per_px`: 1.0 (no calibration, pixels = micrometers)
- `radius_offset_px`: 0.0 (no offset correction)

---

## Testing

### Test Camera Calibration

1. **Set calibration:**
   ```python
   camera.set_calibration(um_per_px=0.82, radius_offset_px=-1.7)
   ```

2. **Verify retrieval:**
   ```python
   cal = camera.get_calibration()
   assert cal['um_per_px'] == 0.82
   assert cal['radius_offset_px'] == -1.7
   ```

3. **Start detection and verify histogram uses calibration:**
   - Check histogram shows values in micrometers
   - Verify unit is "um" when um_per_px != 1.0

### Test Radius Offset

1. **Create test contour with known size**
2. **Measure without offset:**
   ```python
   metrics = measurer.measure([contour], radius_offset_px=0.0)
   ```

3. **Measure with offset:**
   ```python
   metrics_corrected = measurer.measure([contour], radius_offset_px=-2.0)
   ```

4. **Verify offset is applied:**
   - `equivalent_diameter` should be smaller with negative offset
   - Difference should be approximately `2 * offset` (diameter = 2 * radius)

### Test Pull-Based Processing

1. **Start detection**
2. **Rapidly feed many frames**
3. **Verify:**
   - Processing doesn't lag
   - Only latest frames are processed
   - No memory buildup
   - `processing_busy` flag works correctly

---

## Backward Compatibility

### Existing Code
- Still supports global `pixel_ratio` in config
- Falls back to config if camera calibration not available
- Default values maintain existing behavior

### Migration Path
1. Existing configs with `pixel_ratio` continue to work
2. Gradually migrate to camera-specific calibration:
   ```python
   # Old way (still works)
   config.pixel_ratio = 0.82
   
   # New way (recommended)
   camera.set_calibration(um_per_px=0.82)
   ```

---

## Files Modified

1. **`controllers/camera.py`**
   - Added calibration storage
   - Added `get_calibration()` and `set_calibration()` methods

2. **`controllers/droplet_detector_controller.py`**
   - Reads calibration from camera
   - Stores `um_per_px` and `radius_offset_px`
   - Passes offset to detector
   - Implements pull-based processing

3. **`droplet-detection/detector.py`**
   - Added `radius_offset_px` parameter
   - Passes offset to measurer

4. **`droplet-detection/measurer.py`**
   - Added `radius_offset_px` parameter
   - Applies offset correction to measurements

---

## Next Steps (Phase 2)

After Phase 1 is tested and validated:

1. **Processing Rate Display** - Show Hz in UI
2. **Module Enable/Disable** - Conditional initialization
3. **Data Export** - CSV/TXT export functionality

---

## Status

✅ **Camera-specific calibration:** Implemented  
✅ **Radius offset correction:** Implemented  
✅ **Pull-based processing:** Implemented  
⏳ **Testing:** Pending  
⏳ **Documentation:** Complete  

---

**Last Updated:** December 2025
