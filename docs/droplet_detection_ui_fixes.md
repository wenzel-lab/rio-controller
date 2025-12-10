# Droplet Detection UI Fixes
## Issues Fixed

**Date:** December 2025

---

## Issues Identified

1. **Start button not working** - Button click didn't start detection
2. **Histogram plots expanding downward** - Charts growing vertically instead of maintaining fixed size
3. **Graph origin not at 0/0** - Charts not starting at bottom-left origin
4. **X-axis in px instead of um** - Need to convert pixels to micrometers using pixel_ratio

---

## Fixes Applied

### 1. Import Error Fix

**Issue:** `No module named 'droplet_detection'` - Python can't import modules with hyphens in directory names.

**Fix:** Updated `droplet_detector_controller.py` to use `importlib` to dynamically import the `droplet-detection` directory:

```python
# Handle import of droplet-detection (hyphenated directory name)
import importlib.util

droplet_detection_path = os.path.join(software_dir, "droplet-detection")
if os.path.exists(droplet_detection_path):
    spec = importlib.util.spec_from_file_location(
        "droplet_detection",
        os.path.join(droplet_detection_path, "__init__.py")
    )
    droplet_detection = importlib.util.module_from_spec(spec)
    sys.modules["droplet_detection"] = droplet_detection
    spec.loader.exec_module(droplet_detection)
```

**Result:** Module now loads correctly, enabling droplet detection functionality.

---

### 2. Histogram Visualization Fixes

#### Fixed Aspect Ratio

**Issue:** Charts expanding downward without limit.

**Fix:** Set fixed aspect ratio (1:2 height:width) and fixed container height:

```javascript
options: {
    maintainAspectRatio: true,
    aspectRatio: 2,  // Width:Height = 2:1 (height:width = 1:2)
    // ...
}
```

**CSS:**
```javascript
canvas.style.height = '300px';
canvas.style.width = '100%';
card.innerHTML = `
    <div class="card-body" style="position: relative; height: 300px; overflow: hidden;">
        <canvas id="${chartId}" style="max-height: 300px !important;"></canvas>
    </div>
`;
```

**Result:** Charts maintain fixed size and don't expand downward.

---

#### Origin at 0/0

**Issue:** Charts not starting at bottom-left origin.

**Fix:** Explicitly set min values to 0 for both axes:

```javascript
scales: {
    y: {
        beginAtZero: true,
        min: 0,  // Ensure origin at 0
        // ...
    },
    x: {
        beginAtZero: true,
        min: 0,  // Ensure origin at 0
        // ...
    }
}
```

**Result:** All charts start at 0/0 origin.

---

#### X-Axis Unit Conversion (px → um)

**Issue:** X-axis showing pixels instead of micrometers.

**Fix:** 
1. Added `pixel_ratio` and `unit` to histogram JSON output
2. Updated JavaScript to convert pixel values to micrometers
3. Updated axis labels to show correct unit

**Backend (`histogram.py`):**
```python
return {
    "histograms": {...},
    "statistics": {...},
    "pixel_ratio": self.pixel_ratio,  # Include for conversion
    "unit": self.unit,  # Include unit (um or px)
}
```

**Frontend (`droplet_histogram.js`):**
```javascript
// Store pixel ratio and unit
this.pixelRatio = 1.0;
this.unit = 'px';

// In updateHistograms:
if (data.pixel_ratio !== undefined) {
    this.pixelRatio = data.pixel_ratio;
}
if (data.unit) {
    this.unit = data.unit;
}

// Convert bin centers from px to um
const binCenters = [];
for (let i = 0; i < histData.bins.length - 1; i++) {
    const centerPx = (histData.bins[i] + histData.bins[i + 1]) / 2;
    const centerUm = centerPx * this.pixelRatio;  // Convert to um
    binCenters.push(centerUm);
}
```

**Result:** X-axis now displays values in micrometers (um) instead of pixels.

---

### 3. Start Button Error Handling

**Issue:** Start button not providing feedback on errors.

**Fix:** Added comprehensive error handling and logging:

```python
if cmd == "start":
    try:
        success = self.droplet_controller.start()
        if success:
            logger.info("Droplet detection started via WebSocket")
            self._emit_status()
        else:
            logger.warning("Failed to start droplet detection")
            self.socketio.emit("droplet:error", {
                "message": "Failed to start detection. Check ROI is set."
            })
    except Exception as e:
        logger.error(f"Error starting droplet detection: {e}")
        self.socketio.emit("droplet:error", {
            "message": f"Error starting detection: {str(e)}"
        })
```

**Result:** Better error messages and debugging information.

---

## Testing

### Verification Steps

1. **Import Test:**
   ```bash
   python -c "from controllers.droplet_detector_controller import DropletDetectorController; print('✓ Import OK')"
   ```

2. **Start Button:**
   - Set ROI in Camera View tab
   - Go to Droplet Detection tab
   - Click "Start Detection"
   - Should see status change to "Running"
   - Check browser console for any errors

3. **Histogram Display:**
   - Start detection
   - Verify charts maintain fixed size (300px height)
   - Verify charts start at 0/0
   - Verify x-axis shows "Size (um)" instead of "Size (px)"
   - Verify values are in micrometers (not pixels)

---

## Configuration

### Pixel Ratio Setup

The pixel ratio (um/px) should be configured in the `DropletHistogram` initialization:

```python
histogram = DropletHistogram(
    window_size=1000,
    pixel_ratio=0.5,  # e.g., 0.5 um per pixel
    unit="um"
)
```

**Note:** Currently defaults to `pixel_ratio=1.0` and `unit="px"`. This should be configured based on camera calibration.

---

## Files Modified

1. **`controllers/droplet_detector_controller.py`**
   - Fixed import using `importlib` for hyphenated directory name

2. **`droplet-detection/histogram.py`**
   - Added `pixel_ratio` and `unit` to JSON output

3. **`rio-webapp/static/droplet_histogram.js`**
   - Fixed aspect ratio (1:2 height:width)
   - Set origin to 0/0
   - Added pixel to micrometer conversion
   - Fixed container height

4. **`rio-webapp/controllers/droplet_web_controller.py`**
   - Improved error handling for start command

---

## Remaining Work

### Camera Calibration Integration

The pixel ratio should be obtained from camera configuration. Currently it defaults to 1.0. Need to:

1. Add pixel ratio/calibration to camera configuration
2. Pass pixel ratio from camera to droplet detector controller
3. Update histogram initialization with correct pixel ratio

**Example:**
```python
# In camera.py or config
pixel_ratio = camera.get_pixel_ratio()  # um/px

# In droplet_detector_controller.py
self.histogram = DropletHistogram(
    window_size=2000,
    pixel_ratio=pixel_ratio,
    unit="um"
)
```

---

## Status

✅ **Import error fixed** - Module loads correctly  
✅ **Aspect ratio fixed** - Charts maintain 1:2 ratio  
✅ **Origin fixed** - Charts start at 0/0  
✅ **Unit conversion** - X-axis shows um (when pixel_ratio configured)  
✅ **Error handling** - Better feedback on start button

**Next:** Integrate camera calibration for automatic pixel ratio detection.

---

**Last Updated:** December 2025
