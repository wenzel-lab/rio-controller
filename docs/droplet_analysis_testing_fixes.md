# Droplet Analysis Testing Fixes
## Issues Found and Resolved

**Date:** December 10, 2025

---

## Issues Reported

1. **ROI Selection Error**: Error message appears even when ROI is selected
2. **Empty Histograms**: Histograms don't show data even when detection is running
3. **Counter Increasing**: Frame counter increases when pressing "Get Status" button

---

## Root Causes Identified

### Issue 1: Misleading ROI Error Message

**Problem:**
- When detection is already running, clicking "Start" again returns `False`
- The error message always said "Check ROI is set" even when the real issue was "already running"
- This confused users who had already set ROI

**Fix:**
- Added explicit checks before calling `start()`:
  1. Check if detection is already running → Show "already running" message
  2. Check if ROI is set → Show "ROI not set" message
  3. Only then call `start()` and show generic error if it fails

**Files Modified:**
- `rio-webapp/controllers/droplet_web_controller.py` - `_handle_start_command()`

---

### Issue 2: Empty Histograms

**Problem:**
- Histograms were empty even though detection was running
- Multiple possible causes:
  1. Background initialization takes 30 frames (default) - during this time, no droplets are detected
  2. Simulated camera droplets might not be in the ROI region
  3. Droplets might be filtered out by artifact rejection
  4. No logging to diagnose which stage was failing

**Fixes Applied:**

1. **Added Debug Logging:**
   - Log every 10 frames during background initialization
   - Log every 100 frames when no contours found
   - Log every 100 frames when contours are filtered out
   - Log every 50 frames when droplets are successfully detected

2. **Improved Histogram Emission:**
   - Histograms now always emit when `get_status` is called (even if empty)
   - This allows UI to show current state (empty vs. no data)

3. **Better Status Updates:**
   - Statistics always emit when forced (via `get_status`)
   - UI can now show "0 droplets detected" instead of nothing

**Files Modified:**
- `droplet-detection/detector.py` - Added debug logging
- `rio-webapp/controllers/droplet_web_controller.py` - Improved histogram/statistics emission

---

### Issue 3: Counter Increasing on Get Status

**Clarification:**
- This is **expected behavior**, not a bug
- The frame counter increases because:
  - Detection runs continuously in a background thread
  - Frames are processed even when UI is not actively updating
  - `get_status` just displays the current counter value
  - The counter was already increasing; `get_status` just shows the updated value

**No Fix Needed:**
- This is correct behavior
- Counter should increase as frames are processed
- `get_status` button is working as intended

---

## Testing Recommendations

### 1. Test Error Messages

**Steps:**
1. Start detection
2. Try to start again without stopping
3. Verify error message: "Detection is already running. Stop it first to restart."

**Steps:**
1. Don't set ROI
2. Try to start detection
3. Verify error message: "ROI not set. Please select a region of interest in the Camera View tab first."

### 2. Test Background Initialization

**Steps:**
1. Start detection
2. Check console logs
3. Look for: "Initializing background: frame X/30"
4. Wait 30+ frames (about 1-2 seconds at 30 FPS)
5. Check if droplets start appearing in histograms

**Expected:**
- First 30 frames: Background initializing, no droplets detected
- After 30 frames: Droplets should start appearing (if simulated camera generates them in ROI)

### 3. Test Empty Histogram Display

**Steps:**
1. Start detection
2. Wait for background initialization
3. Press "Get Status" button
4. Check if histograms show (even if empty)

**Expected:**
- Histograms should display with empty data
- Statistics should show "0" for all metrics
- Frame count should be increasing

### 4. Test Simulated Camera Droplets

**Issue:** Simulated camera generates droplets, but they might not be in your ROI.

**Steps:**
1. Check simulated camera settings:
   - Default: `generate_droplets=True`
   - Default: 5 droplets per frame
   - Droplets move randomly across the frame

2. **Solution:** Make ROI large enough to capture moving droplets
   - Set ROI to cover most of the frame
   - Or wait for droplets to move into ROI region

3. **Alternative:** Check if droplets are being filtered
   - Look for log messages: "X contours found, all filtered out by artifact rejection"
   - If this appears, artifact rejection might be too strict

### 5. Test Debug Logging

**Steps:**
1. Start detection
2. Monitor console output
3. Look for debug messages:
   - `"Initializing background: frame X/30"` (every 10 frames)
   - `"Frame X: No contours detected"` (every 100 frames)
   - `"Frame X: Y contour(s) found, all filtered out"` (every 100 frames)
   - `"Frame X: Y droplet(s) detected"` (every 50 frames when successful)

**Expected:**
- Logs help diagnose why droplets aren't detected
- If you see "No contours detected" → Droplets not in ROI or preprocessing issue
- If you see "all filtered out" → Artifact rejection too strict

---

## Common Scenarios

### Scenario 1: Histograms Empty After 30 Frames

**Possible Causes:**
1. Simulated camera droplets not in ROI region
2. Droplets filtered out by artifact rejection
3. Preprocessing parameters too strict

**Diagnosis:**
- Check console logs for debug messages
- Check if `droplet_count_total` is increasing
- Try larger ROI
- Try adjusting `min_area` and `max_area` in config

### Scenario 2: "Detection Already Running" Error

**Cause:**
- Detection is already running from previous start

**Solution:**
- Click "Stop" button first
- Then click "Start" again

### Scenario 3: ROI Error When ROI Is Set

**Cause:**
- ROI might have been cleared or changed
- Detection might be running with old ROI

**Solution:**
- Set ROI again in Camera View tab
- Stop detection if running
- Start detection again

---

## Configuration Adjustments

If droplets are not being detected, try adjusting these parameters:

```python
# Via API or config file
{
    "min_area": 10,        # Lower minimum area (default: 20)
    "max_area": 10000,     # Higher maximum area (default: 5000)
    "min_aspect_ratio": 0.3,  # More lenient (default: 0.5)
    "max_aspect_ratio": 3.0,  # More lenient (default: 2.0)
    "use_frame_diff": false,  # Disable frame diff (if too strict)
    "min_motion": 0.5,     # Lower motion threshold (default: 1.0)
}
```

---

## Next Steps for Testing

1. **Test with Real Camera:**
   - Simulated camera droplets might not match real conditions
   - Test with actual microfluidics setup

2. **Adjust Detection Parameters:**
   - If droplets are filtered out, adjust `min_area`, `max_area`, `min_motion`
   - Check artifact rejection settings

3. **Monitor Logs:**
   - Enable debug logging to see what's happening
   - Look for patterns in detection failures

4. **Verify ROI:**
   - Ensure ROI covers the channel where droplets flow
   - Make ROI large enough to capture moving droplets

---

## Files Modified

1. `rio-webapp/controllers/droplet_web_controller.py`
   - Improved error messages in `_handle_start_command()`
   - Enhanced `emit_histogram()` and `emit_statistics()` to always emit when forced

2. `droplet-detection/detector.py`
   - Added debug logging for background initialization
   - Added debug logging for contour detection
   - Added debug logging for artifact rejection
   - Added debug logging for successful detections

---

## Summary

- ✅ **Fixed:** Misleading ROI error message (now distinguishes "already running" vs "ROI not set")
- ✅ **Fixed:** Histograms not showing when empty (now always emit on `get_status`)
- ✅ **Added:** Debug logging to diagnose detection issues
- ℹ️ **Clarified:** Counter increasing is expected behavior (frames processed continuously)

**Status:** Ready for testing with improved error messages and diagnostic logging.
