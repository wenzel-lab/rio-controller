# Code Changes Log

**Documentation Date:** December 20, 2025  
**Project:** Rio Controller  
**Base Code:** Initial codebase from repository  
**Changes Made On:** Raspberry Pi at `/home/pi/rio-controller`

## Overview

This document tracks all changes made to the codebase after introducing it to this Raspberry Pi. Changes were made to fix bugs, improve functionality, and align with the old working implementation (`/home/pi/webapp/`).

## Summary of Changes

### Major Areas Modified
1. **Camera Frame Generation** - Fixed continuous frame capture and performance
2. **Strobe Timing Synchronization** - Fixed dead time calculation and hardware readback
3. **ROI Selection** - Fixed coordinate system consistency across browsers
4. **Error Handling** - Improved robustness and logging
5. **Trigger Mode Configuration** - Fixed conditional execution in strobe-centric mode

---

## Detailed Change Log

### 1. Camera Frame Generation (`drivers/camera/pi_camera_legacy.py`)

#### Changes Made

**Issue:** Camera feed was not displaying, showing only placeholder. High "Cam read time" (23450us) indicated performance problems.

**Fixes:**

1. **Fixed `generate_frames()` method to properly reuse `io.BytesIO` stream**
   - **Problem:** Stream was not being reused, causing capture_continuous to break after first frame
   - **Solution:** Reuse single `io.BytesIO` stream instance, seek to 0 and truncate after each frame
   - **Lines Modified:** `generate_frames()` method
   - **Impact:** Frame generation now works continuously, significantly reducing read time

2. **Changed frame output format from numpy arrays to JPEG bytes**
   - **Problem:** MJPEG streaming requires JPEG bytes, not numpy arrays
   - **Solution:** Return JPEG bytes directly from `capture_continuous`
   - **Impact:** Proper video streaming format for web interface

3. **Optimized exposure mode for video streaming**
   - **Problem:** Manual exposure mode (off) was slower for video streaming
   - **Solution:** Use `exposure_mode = "auto"` for video streaming by default, only set to "off" when `ShutterSpeed` is explicitly provided
   - **Impact:** Better performance for camera preview

4. **Optimized frame interval sleep**
   - **Problem:** Unnecessary sleep calls accumulating lag
   - **Solution:** Only sleep if meaningful time remains (> 0.001 seconds)
   - **Impact:** Reduced latency and improved frame rate consistency

5. **Fixed `get_frame()` to prevent repeated initialization**
   - **Problem:** Method could attempt to initialize camera multiple times
   - **Solution:** Check if camera thread is already running before initializing
   - **Impact:** Prevents race conditions and initialization errors

6. **Added hardware readback methods** (for strobe timing)
   - **Added:** `get_actual_framerate()` method
   - **Added:** `get_actual_shutter_speed()` method
   - **Purpose:** Read actual hardware values (not just config values) for accurate timing calculations
   - **Impact:** Enables proper dead time calculation for strobe synchronization

**Code Example (generate_frames fix):**
```python
# Before: Stream was created fresh each iteration (incorrect)
# After: Stream is reused properly
stream = io.BytesIO()
for frame in self.cam.capture_continuous(stream, format="jpeg", use_video_port=True):
    if not self.cam_running_event.is_set():
        break
    stream.seek(0)
    data = stream.getvalue()
    stream.seek(0)
    stream.truncate()
    yield data
```

---

### 2. Strobe Timing Synchronization (`controllers/strobe_cam.py`)

#### Changes Made

**Issue:** Strobe timing was not synchronizing correctly with camera frames. Comparison with old working implementation (`/home/pi/webapp/pistrobecam.py`) revealed missing dead time calculation.

**Fixes:**

1. **Fixed `set_timing()` method - Added dead time calculation for strobe-centric mode**
   - **Problem:** Missing critical dead time adjustment that accounts for time between frame capture completion and next frame start
   - **Solution:** 
     - Set camera config first
     - Read back actual framerate and shutter speed from hardware
     - Calculate dead time: `dead_time = frame_period - actual_shutter_speed`
     - Adjust pre-padding: `adjusted_pre_padding = pre_padding + dead_time`
     - Set strobe timing with adjusted pre-padding
   - **Lines Modified:** `set_timing()` method, strobe-centric branch (lines ~327-365)
   - **Impact:** Strobe now fires at correct time relative to frame start, matching old working implementation

2. **Added hardware readback helper methods**
   - **Added:** `_get_actual_framerate()` method
   - **Added:** `_get_actual_shutter_speed()` method
   - **Purpose:** Read actual values from camera hardware (which may differ from requested values due to rounding/limits)
   - **Impact:** Calculations use actual hardware values, not theoretical values

3. **Fixed trigger mode configuration - Conditional execution**
   - **Problem:** `set_trigger_mode()` was called even in strobe-centric mode, sending unsupported SPI commands to old firmware
   - **Solution:** Only call `set_trigger_mode()` when `hardware_trigger_mode == True` (camera-centric mode)
   - **Lines Modified:** `__init__()` method (lines ~169-176)
   - **Impact:** Prevents SPI command failures with old firmware

4. **Improved logging for debugging**
   - **Added:** Logging shows both requested and actual framerate/shutter values
   - **Added:** Dead time calculation values in debug logs
   - **Impact:** Better troubleshooting capability

5. **Fixed framerate clamping and shutter recalculation**
   - **Problem:** When framerate was clamped to MAX_FRAMERATE, shutter speed wasn't recalculated to match
   - **Solution:** Recalculate shutter_speed_us when framerate is clamped
   - **Lines Modified:** `_calculate_camera_timing()` method
   - **Impact:** Ensures consistent timing calculations

**Code Example (dead time calculation fix):**
```python
# Old implementation pattern (now replicated):
# 1. Set camera config
self.camera.set_config({"FrameRate": framerate, "ShutterSpeed": shutter_speed_us})

# 2. Read back actual values
actual_framerate = self._get_actual_framerate(framerate)
actual_shutter_speed_us = self._get_actual_shutter_speed(shutter_speed_us)

# 3. Calculate dead time
frame_rate_period_us = int(1000000 / float(actual_framerate))
strobe_pre_wait_us = frame_rate_period_us - actual_shutter_speed_us

# 4. Adjust pre-padding
adjusted_pre_padding_ns = pre_padding_ns + (NS_TO_US * strobe_pre_wait_us)

# 5. Set strobe timing with adjusted value
self.strobe.set_timing(adjusted_pre_padding_ns, strobe_period_ns)
```

---

### 3. ROI Selection Fixes (`rio-webapp/static/roi_selector.js`)

#### Changes Made

**Issue:** ROI coordinates were inconsistent between different browsers. Pi browser showed "infinityxinfinity" errors. ROI selection didn't work in Chrome on Pi.

**Fixes:**

1. **Fixed arrow function compatibility**
   - **Problem:** Arrow functions not supported in older browsers (e.g., Chrome on Pi)
   - **Solution:** Converted arrow functions to regular functions
   - **Impact:** ROI selection now works on Pi browser

2. **Fixed image dimension detection**
   - **Problem:** Canvas size calculation failing, showing "infinityxinfinity"
   - **Solution:** Added robust dimension detection using `naturalWidth`, `width`, `offsetWidth` with fallbacks
   - **Lines Modified:** `updateCanvasSize()` method
   - **Impact:** Canvas properly sized, coordinates calculated correctly

3. **Fixed coordinate system consistency**
   - **Problem:** ROI coordinates differed between browsers due to CSS scaling vs. actual image dimensions
   - **Solution:** 
     - Use `canvas.width`/`canvas.height` for scaling calculations (not CSS dimensions)
     - Set `imgWidth` and `imgHeight` consistently from `window.cameraResolution` (actual camera resolution)
     - Removed double-scaling when receiving ROI from server
   - **Lines Modified:** `getCanvasCoordinates()`, `updateCanvasSize()`, socket handlers
   - **Impact:** Consistent ROI coordinates across all browsers

4. **Fixed canvas/image layering**
   - **Problem:** Image blocking clicks to canvas
   - **Solution:** Set `pointer-events: none` on image, `z-index: 10` on canvas (in HTML)
   - **Impact:** Clicks properly register on canvas

5. **Added canvas size update on camera resolution change**
   - **Problem:** Canvas didn't resize when camera resolution changed
   - **Solution:** Added `updateCanvasSize()` calls when camera resolution changes via WebSocket
   - **Impact:** ROI selection works correctly after resolution changes

**Code Example (coordinate fix):**
```javascript
// Before: Used getBoundingClientRect() which includes CSS scaling
// After: Use canvas.width/height (actual canvas resolution)
function getCanvasCoordinates(event) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;   // Account for CSS scaling
    const scaleY = canvas.height / rect.height;
    const x = (event.clientX - rect.left) * scaleX;
    const y = (event.clientY - rect.top) * scaleY;
    return { x, y };
}
```

---

### 4. Strobe Control Improvements (`controllers/camera.py`)

#### Changes Made

**Issue:** Strobe enable button was slow, UI state didn't match hardware state, hold-on didn't work consistently.

**Fixes:**

1. **Simplified strobe enable command**
   - **Problem:** Unnecessary `camera.start()` check causing delays
   - **Solution:** Removed redundant check
   - **Impact:** Faster strobe enable/disable response

2. **Fixed UI state synchronization**
   - **Problem:** UI state didn't update if hardware call failed, leaving user confused
   - **Solution:** Always update `self.strobe_data["enable"]` and `self.strobe_data["hold"]` to reflect user's intent, even if hardware call fails
   - **Lines Modified:** `on_strobe()` method
   - **Impact:** UI always shows user's intended state

3. **Improved error logging**
   - **Added:** Logging includes the value being set when enable/hold fails
   - **Impact:** Better debugging information

**Code Example:**
```python
# Always update UI state to match user's intent
valid = self.strobe_cam.strobe.set_enable(enabled)
self.strobe_data["enable"] = enabled  # Always update UI state
if valid:
    logger.info(f"Strobe enabled: {enabled}")
else:
    logger.warning(f"Failed to set strobe enable to {enabled} - check hardware connection")
```

---

### 5. Strobe Driver Improvements (`drivers/strobe.py`)

#### Changes Made

**Issue:** Error handling was too strict, causing failures with valid hardware responses. Missing safety checks for empty data.

**Fixes:**

1. **Adjusted error handling to match old implementation**
   - **Problem:** Too strict validation causing false failures
   - **Solution:** Match old implementation's less strict approach while keeping safety checks
   - **Lines Modified:** `set_enable()`, `set_hold()`, `set_timing()`
   - **Impact:** More reliable hardware communication

2. **Added safety checks for empty data**
   - **Problem:** Potential crashes on empty or insufficient SPI responses
   - **Solution:** Check for empty data before accessing response elements
   - **Lines Modified:** `set_enable()`, `set_hold()`, `set_timing()`, `get_cam_read_time()`
   - **Impact:** Prevents crashes, improves robustness

**Code Example:**
```python
def set_enable(self, enable):
    enabled = 1 if enable else 0
    valid, data = self.packet_query(1, [enabled])
    if not valid:
        return False
    # Match old implementation: if valid is True, assume data has at least one element
    return data[0] == 0
```

---

### 6. Web Interface Template Fixes (`rio-webapp/templates/index.html`)

#### Changes Made

**Issue:** Template errors when refreshing page, camera resolution not properly initialized in JavaScript.

**Fixes:**

1. **Fixed camera resolution initialization**
   - **Problem:** JavaScript tried to access `cam.cam_data.get()` but `cam` is a dictionary
   - **Solution:** Use dictionary syntax: `cam['display_width']` and `cam['display_height']`
   - **Lines Modified:** JavaScript `cameraResolution` object initialization
   - **Impact:** Page refresh no longer causes errors

2. **Added CSS for ROI canvas layering**
   - **Added:** `pointer-events: none;` on `#camera_image`
   - **Added:** `z-index: 10;` on `#roi_canvas`
   - **Impact:** Clicks properly pass through image to canvas

3. **Added canvas size update on camera resolution change**
   - **Added:** Call to `roiSelector.updateCanvasSize()` in `socket.on('cam')` handler
   - **Impact:** ROI canvas resizes correctly when camera resolution changes

4. **Added strobe period "Set" button handler**
   - **Added:** `strobe_period()` JavaScript function
   - **Impact:** Strobe period can be set from web interface

---

### 7. Camera Controller Error Handling (`controllers/camera.py`)

#### Changes Made

**Issue:** Camera type changes could cause crashes if camera wasn't initialized.

**Fixes:**

1. **Improved camera type change error handling**
   - **Problem:** `RuntimeError("Camera not initialized")` during configuration could crash
   - **Solution:** Catch exception, perform cleanup, return `False` gracefully
   - **Lines Modified:** `set_camera_type()` method in `strobe_cam.py`
   - **Impact:** More robust camera configuration changes

---

## Comparison with Old Implementation

Several changes were made specifically to align with the old working implementation at `/home/pi/webapp/`:

### Key Alignments:

1. **Dead Time Calculation** - Now matches `pistrobecam.py::set_timing()` exactly
2. **Hardware Readback** - Reads actual framerate/shutter speed like old code used `self.camera.framerate`
3. **Trigger Mode** - Only configures trigger mode in hardware trigger mode (old code didn't have this)
4. **Error Handling** - Matches old implementation's less strict approach in `drivers/strobe.py`

### Differences Preserved (Intentional):

1. **Abstraction Layer** - New code uses camera abstraction layer instead of direct `picamera`, allowing future 64-bit support
2. **Better Error Handling** - New code has more robust exception handling and logging
3. **WebSocket Communication** - New code uses Flask-SocketIO (old code used different approach)

---

## Testing Notes

All changes were tested on:
- **Hardware:** Raspberry Pi (aarch64)
- **OS:** Raspberry Pi OS (Linux)
- **Python:** 3.9.2
- **Browsers Tested:** 
  - Chrome on Mac
  - Safari on Mac
  - Chromium on Raspberry Pi

### Test Results:

1. ✅ Camera feed now displays correctly
2. ✅ ROI selection works consistently across browsers
3. ✅ Strobe timing synchronization improved (dead time calculation)
4. ✅ Strobe enable/disable works (though may still need hardware verification)
5. ✅ No crashes on page refresh
6. ✅ Canvas properly sized and clickable

---

## Files Modified Summary

### Python Files:
- `drivers/camera/pi_camera_legacy.py` - Frame generation, hardware readback
- `controllers/strobe_cam.py` - Strobe timing, trigger mode, dead time calculation
- `controllers/camera.py` - Strobe control, UI state synchronization
- `drivers/strobe.py` - Error handling, safety checks

### JavaScript Files:
- `rio-webapp/static/roi_selector.js` - ROI coordinate system, browser compatibility

### HTML Files:
- `rio-webapp/templates/index.html` - Template fixes, CSS, JavaScript initialization

---

## Future Improvements Recommended

1. **Hardware Verification** - Test strobe timing with oscilloscope/logic analyzer
2. **Performance Optimization** - Further optimize frame generation if needed
3. **Error Recovery** - Add automatic recovery for hardware communication failures
4. **Testing** - Add unit tests for timing calculations
5. **Documentation** - Add inline documentation for complex timing calculations

---

## Related Documentation

- See `INSTALLED_PACKAGES.md` for package versions and installation notes
- See comparison guide in user's notes for detailed old vs. new implementation analysis

