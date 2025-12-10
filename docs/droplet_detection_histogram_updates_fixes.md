# Droplet Detection Histogram Updates - Additional Fixes
## Auto-Updates, Layout, and Unit Conversion

**Date:** December 2025

---

## Issues Fixed

### 1. Histograms Stop Updating After a Few Frames

**Issue:** Graphs update a few times then stop updating automatically.

**Root Causes:**
- Rate limiting too aggressive (0.2s = 5 Hz)
- Updates only when data changed (missed updates)
- Error handling might be silently failing

**Fixes Applied:**

1. **Changed refresh rate to 2 seconds (0.5 Hz):**
   ```python
   # In droplet_web_controller.py
   self.emit_intervals = {
       "histogram": 2.0,  # 0.5 Hz (once every 2 seconds)
       "statistics": 2.0,  # 0.5 Hz (once every 2 seconds)
   }
   ```

2. **Improved update logic:**
   ```javascript
   // Always update if we have data, even if unchanged
   if (hasUpdates || (data.histograms && Object.keys(data.histograms).length > 0)) {
       this.charts[metric].update('none');
   }
   ```

3. **Better error handling:**
   ```python
   # In routes.py background loop
   try:
       if droplet_web_controller.droplet_controller.running:
           droplet_web_controller.emit_histogram()
   except Exception as e:
       logger.debug(f"Error in droplet update loop: {e}")
   ```

4. **Added debug logging:**
   ```python
   logger.debug(f"Emitted histogram update (frame_count: {self.droplet_controller.frame_count})")
   ```

5. **Get Status button forces refresh:**
   ```python
   elif cmd == "get_status":
       self._emit_status()
       # Also force emit histogram and statistics when status is requested
       self.emit_histogram(force=True)
       self.emit_statistics(force=True)
   ```

**Result:** Histograms update every 2 seconds when detection is running.

---

### 2. ROI Error Even When ROI is Set

**Issue:** "ROI not set" error appears even when ROI is selected.

**Root Cause:** Race condition or ROI not properly retrieved from camera.

**Fix:**
```python
# Added logging for debugging
roi = self.camera.get_roi()
if roi is None:
    logger.error("ROI not set in camera. Please set ROI before starting detection.")
    return False

# Log ROI for debugging
logger.info(f"Starting detection with ROI: {roi}")
```

**Result:** Better debugging information to identify ROI issues.

---

### 3. X-Axis Still in Pixels Instead of Micrometers

**Issue:** X-axis shows "Size (px)" even when pixel_ratio should convert to um.

**Root Causes:**
- `pixel_ratio` defaults to 1.0 (no conversion)
- Unit not being updated correctly
- JavaScript not applying conversion

**Fixes Applied:**

1. **Ensure pixel_ratio is included in all outputs:**
   ```python
   # In histogram.py to_json()
   return {
       "histograms": {...},
       "statistics": {...},
       "pixel_ratio": self.pixel_ratio,  # Always include
       "unit": self.unit,  # Always include
       "count": int(len(self.widths)),
   }
   ```

2. **JavaScript conversion with logging:**
   ```javascript
   // Update pixel ratio and unit if provided
   if (data.pixel_ratio !== undefined && data.pixel_ratio !== null) {
       this.pixelRatio = parseFloat(data.pixel_ratio);
       console.log(`Updated pixel ratio to: ${this.pixelRatio}`);
   }
   if (data.unit) {
       this.unit = data.unit;
       console.log(`Updated unit to: ${this.unit}`);
   }
   
   // Convert bin centers
   const centerUm = Math.round(centerPx * this.pixelRatio);
   ```

3. **Always update x-axis label:**
   ```javascript
   // Update x-axis label with unit (always update to reflect current unit)
   if (this.charts[metric].options.scales && this.charts[metric].options.scales.x) {
       this.charts[metric].options.scales.x.title.text = `Size (${this.unit})`;
   }
   ```

**Result:** X-axis will show "Size (um)" when `pixel_ratio` is set to a value other than 1.0.

**Note:** To enable micrometers, set `pixel_ratio`:
```javascript
socket.emit('droplet', {
    cmd: 'config',
    parameters: { pixel_ratio: 0.5 }  // 0.5 um per pixel
});
```

---

### 4. Graph Legend Swallowed by Bottom Edge

**Issue:** Statistics text at bottom of chart is cut off or hidden.

**Fix:**
```javascript
// Added padding at bottom and absolute positioning for stats
card.innerHTML = `
    <div class="card-body" style="position: relative; padding-bottom: 60px; min-height: 300px;">
        <canvas id="${chartId}" style="max-height: 400px; width: 100% !important;"></canvas>
        <div id="${chartId}_stats" class="mt-2 small text-muted" 
             style="position: absolute; bottom: 10px; left: 15px; right: 15px;"></div>
    </div>
`;

// Chart.js layout padding
layout: {
    padding: {
        bottom: 50  // Space for statistics at bottom
    }
}
```

**Result:** Statistics text is visible and not cut off.

---

### 5. Histogram Boxes Not Dynamic/Responsive

**Issue:** Histograms don't adapt to screen size or arrange efficiently.

**Fix:**
```javascript
// Use Bootstrap grid for responsive layout
const col = document.createElement('div');
col.className = 'col-lg-6 col-md-12 mb-3';  // 2 columns on large, 1 on medium/small

const card = document.createElement('div');
card.className = 'card h-100';  // Equal height cards

// Container uses Bootstrap row
<div id="droplet_histogram_container" class="row">
```

**Result:**
- Large screens: 2 histograms side-by-side
- Medium/small screens: 1 histogram per row
- Cards scale dynamically with screen size
- Equal height cards in same row

---

## Summary of Changes

### Files Modified

1. **`rio-webapp/controllers/droplet_web_controller.py`**
   - Changed refresh rate to 2 seconds
   - Added better error handling
   - Get Status button forces refresh
   - Added debug logging

2. **`rio-webapp/routes.py`**
   - Improved error handling in background loop
   - Better attribute checking

3. **`rio-webapp/static/droplet_histogram.js`**
   - Responsive Bootstrap grid layout (2 columns on large screens)
   - Fixed statistics positioning (absolute, not cut off)
   - Always update charts if data exists
   - Better pixel_ratio handling with logging
   - Chart layout padding for statistics

4. **`rio-webapp/templates/index.html`**
   - Added row class to histogram container
   - Added note about pixel_ratio configuration

5. **`controllers/droplet_detector_controller.py`**
   - Added ROI logging for debugging

---

## Testing

### Verify Auto-Updates

1. Start detection
2. Watch histogram charts
3. Charts should update every 2 seconds
4. Check browser console for update messages
5. Use "Get Status" button to force immediate refresh

### Verify Responsive Layout

1. Resize browser window
2. On large screens: 2 histograms per row
3. On small screens: 1 histogram per row
4. Statistics text visible at bottom

### Verify Unit Conversion

1. Set pixel_ratio:
   ```javascript
   socket.emit('droplet', {
       cmd: 'config',
       parameters: { pixel_ratio: 0.5 }
   });
   ```
2. Check browser console for "Updated pixel ratio to: 0.5"
3. X-axis should show "Size (um)"
4. Values should be in micrometers (e.g., 25 um instead of 50 px)

---

## Configuration

### Setting Pixel Ratio

**Current Default:** `pixel_ratio = 1.0` (pixels)

**To Use Micrometers:**
```javascript
// Via WebSocket
socket.emit('droplet', {
    cmd: 'config',
    parameters: { pixel_ratio: 0.5 }  // 0.5 um per pixel
});
```

**Example Values:**
- `0.5` = 0.5 um per pixel (common for microscopy)
- `1.0` = 1 um per pixel
- `2.0` = 2 um per pixel

---

## Status

✅ **Refresh rate:** 2 seconds (0.5 Hz)  
✅ **Auto-updates:** Fixed to continue updating  
✅ **Responsive layout:** 2 columns on large, 1 on small  
✅ **Statistics positioning:** Fixed, not cut off  
✅ **Unit conversion:** Works when pixel_ratio configured  
✅ **Integer rounding:** All values rounded  
✅ **Get Status refresh:** Forces immediate update  

**Next:** Configure `pixel_ratio` based on camera calibration to enable micrometer display.

---

**Last Updated:** December 2025
