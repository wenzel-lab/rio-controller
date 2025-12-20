# Pi Code Changes Analysis and Recommendations

**Analysis Date:** December 20, 2025  
**Source:** Code copied from Raspberry Pi (`pi-code-analysis/pi-code/`)  
**Reference:** `CODE_CHANGES.md` in Pi code directory  
**Context:** Changes made during troubleshooting strobe synchronization issues

---

## Executive Summary

The Pi code contains **critical fixes** for strobe-centric mode synchronization that must be adopted, along with several improvements. However, it also includes some changes that should **NOT** be adopted because they revert newer features (hardware ROI, slider-based ROI, display FPS optimization) that were intentionally added to the repository.

**Key Findings:**
1. ✅ **CRITICAL: Dead time calculation** - Must adopt (fixes strobe synchronization)
2. ✅ **IMPORTANT: Hardware readback methods** - Must adopt (required for dead time calculation)
3. ✅ **IMPORTANT: Conditional trigger mode** - Must adopt (prevents firmware compatibility issues)
4. ✅ **MODERATE: Camera frame generation fixes** - Should adopt (performance improvements)
5. ❌ **DO NOT ADOPT: ROI handling changes** - Reverts to older canvas-based approach, conflicts with newer slider-based UI
6. ❌ **DO NOT ADOPT: Removal of hardware ROI** - Removes recently added feature that's better
7. ❌ **DO NOT ADOPT: Removal of CAMERA_DISPLAY_FPS** - Removes useful Pi load optimization

---

## Detailed Analysis by Category

### Category 1: CRITICAL FIXES - Must Adopt ✅

These fixes are essential for strobe-centric mode to work correctly.

#### 1.1 Dead Time Calculation in Strobe-Centric Mode

**File:** `controllers/strobe_cam.py`  
**Priority:** ⚠️ **CRITICAL**  
**Recommendation:** ✅ **ADOPT IMMEDIATELY**

**What Changed:**
- Added dead time calculation for strobe-centric mode (software trigger)
- Calculates: `dead_time = frame_period - actual_shutter_speed`
- Adjusts pre-padding: `adjusted_pre_padding = pre_padding + dead_time`
- Sets strobe timing with adjusted pre-padding

**Why Critical:**
This matches the old working implementation and is essential for proper strobe synchronization. Without this, the strobe fires at the wrong time relative to frame capture.

**Code Location (Pi):**
```python
# In set_timing(), strobe-centric branch (lines ~330-365)
actual_framerate = self._get_actual_framerate(framerate)
actual_shutter_speed_us = self._get_actual_shutter_speed(shutter_speed_us)
frame_rate_period_us = int(1000000 / float(actual_framerate))
strobe_pre_wait_us = frame_rate_period_us - actual_shutter_speed_us
adjusted_pre_padding_ns = pre_padding_ns + (NS_TO_US * strobe_pre_wait_us)
self.strobe.set_timing(adjusted_pre_padding_ns, strobe_period_ns)
```

**Repository Status:**
- ❌ Currently missing in `software/controllers/strobe_cam.py`
- Matches issues identified in `strobe-centric-mode-comparison-and-issues.md`

**Adoption Notes:**
- Only applies to strobe-centric mode (software trigger)
- Requires hardware readback methods (see 1.2)
- Order of operations matters: set camera config first, then read back, then calculate

---

#### 1.2 Hardware Readback Methods

**Files:** 
- `controllers/strobe_cam.py` - Helper methods `_get_actual_framerate()`, `_get_actual_shutter_speed()`
- `drivers/camera/pi_camera_legacy.py` - Implementation methods `get_actual_framerate()`, `get_actual_shutter_speed()`

**Priority:** ⚠️ **CRITICAL**  
**Recommendation:** ✅ **ADOPT IMMEDIATELY**

**What Changed:**
- Added methods to read actual framerate and shutter speed from camera hardware
- Returns actual values (may differ from requested due to hardware rounding/limits)
- Used by dead time calculation to get accurate timing

**Why Critical:**
Dead time calculation requires actual hardware values, not theoretical values. Camera hardware may round or clamp framerate/shutter values.

**Code Location (Pi):**
- `pi_camera_legacy.py` lines ~268-300: `get_actual_framerate()`, `get_actual_shutter_speed()`
- `strobe_cam.py` lines ~402-440: `_get_actual_framerate()`, `_get_actual_shutter_speed()`

**Repository Status:**
- ❌ Missing in repository code
- Identified as needed in `strobe-centric-mode-comparison-and-issues.md`

**Adoption Notes:**
- Must be added to both `BaseCamera` interface (abstract method) and implementations
- `PiCameraLegacy` should read from `self.cam.framerate` and `self.cam.shutter_speed`
- `PiCameraV2` should read from picamera2 controls if available

---

#### 1.3 Conditional Trigger Mode Configuration

**File:** `controllers/strobe_cam.py`  
**Priority:** ⚠️ **IMPORTANT**  
**Recommendation:** ✅ **ADOPT**

**What Changed:**
- Only calls `set_trigger_mode()` when `hardware_trigger_mode == True` (camera-centric mode)
- Skips trigger mode configuration in strobe-centric mode
- Prevents sending unsupported SPI command to old firmware

**Why Important:**
Old firmware doesn't support `PACKET_TYPE_SET_TRIGGER_MODE` (type 5). Calling it in strobe-centric mode causes SPI failures.

**Code Location (Pi):**
```python
# In __init__(), lines ~169-178
if self.hardware_trigger_mode:
    try:
        self.strobe.set_trigger_mode(True)
        logger.debug("Strobe configured for hardware trigger mode")
    except Exception as e:
        logger.error(f"Error configuring strobe trigger mode: {e}")
        raise
else:
    logger.debug("Strobe-centric mode: trigger mode configuration skipped (not needed)")
```

**Repository Status:**
- ❌ Currently calls `set_trigger_mode()` unconditionally (line ~161 in repo)
- Matches issue identified in comparison document

**Adoption Notes:**
- Simple fix - wrap existing call in conditional
- Should only apply to camera-centric mode

---

### Category 2: IMPORTANT IMPROVEMENTS - Should Adopt ✅

These improve reliability, performance, and error handling.

#### 2.1 Camera Frame Generation Fixes

**File:** `drivers/camera/pi_camera_legacy.py`  
**Priority:** ⚠️ **IMPORTANT**  
**Recommendation:** ✅ **ADOPT** (with verification)

**What Changed:**
1. **Fixed `generate_frames()` to reuse `io.BytesIO` stream** - Prevents `capture_continuous` from breaking after first frame
2. **Changed output format to JPEG bytes** - Required for MJPEG streaming
3. **Optimized exposure mode** - Uses "auto" for video streaming unless shutter speed explicitly set
4. **Optimized frame interval sleep** - Only sleeps if meaningful time remains (> 0.001s)

**Why Important:**
Fixes camera feed not displaying and high "Cam read time" issues. Significantly improves performance.

**Code Location (Pi):**
- `generate_frames()` method, lines ~83-127

**Repository Status:**
- ❓ Needs comparison with current repo implementation
- May already be partially fixed in newer repo code

**Adoption Notes:**
- Verify current repo code doesn't already have these fixes
- May conflict with other camera optimizations
- Test frame generation performance after adoption

---

#### 2.2 Camera Initialization Error Handling

**File:** `controllers/strobe_cam.py`  
**Priority:** ⚠️ **MODERATE**  
**Recommendation:** ✅ **ADOPT** (with care)

**What Changed:**
- Added try-except around camera initialization
- Gracefully handles `RuntimeError("Camera not initialized")`
- Continues without camera if hardware unavailable (simulation mode)
- Prevents crashes during camera type changes

**Code Location (Pi):**
- `__init__()` method, lines ~133-146
- `set_camera_type()` method, lines ~215-233

**Repository Status:**
- ❓ Current repo error handling needs review

**Adoption Notes:**
- Good defensive programming
- Make sure error messages are clear
- Don't silently fail in production - logging is important

---

#### 2.3 Strobe Driver Error Handling Improvements

**File:** `drivers/strobe.py`  
**Priority:** ⚠️ **MODERATE**  
**Recommendation:** ✅ **ADOPT**

**What Changed:**
- Added safety checks for empty data in SPI responses
- Improved validation in `set_enable()`, `set_hold()`, `set_timing()`, `get_cam_read_time()`
- Matches old implementation's less strict approach while keeping safety checks

**Code Location (Pi):**
- Multiple methods, lines ~109-145

**Repository Status:**
- ❌ Current repo has stricter validation

**Adoption Notes:**
- Prevents crashes on malformed SPI responses
- Balances strictness with robustness
- Test with actual hardware to verify

---

#### 2.4 Framerate Clamping Fix

**File:** `controllers/strobe_cam.py`  
**Priority:** ⚠️ **MODERATE**  
**Recommendation:** ✅ **ADOPT**

**What Changed:**
- When framerate is clamped to MAX_FRAMERATE, shutter speed is recalculated to match
- Ensures timing calculations remain consistent

**Code Location (Pi):**
- `_calculate_camera_timing()` method, lines ~394-398

**Repository Status:**
- ❓ Needs verification if repo already does this

**Adoption Notes:**
- Small but important fix
- Prevents timing inconsistencies

---

#### 2.5 Strobe Control UI State Synchronization

**File:** `controllers/camera.py`  
**Priority:** ⚠️ **MODERATE**  
**Recommendation:** ✅ **ADOPT** (with consideration)

**What Changed:**
- Always updates `strobe_data["enable"]` and `strobe_data["hold"]` to match user intent
- Updates UI state even if hardware call fails
- Prevents user confusion when hardware call fails silently

**Code Location (Pi):**
- `on_strobe()` method, lines ~797-833

**Repository Status:**
- ❌ Current repo only updates UI state if hardware call succeeds

**Adoption Notes:**
- Improves UX - UI reflects user's intent
- May mask hardware failures - ensure logging is adequate
- Consider adding visual indicator when hardware state differs from UI state

---

#### 2.6 Camera Thread Initialization Check

**File:** `controllers/camera.py`  
**Priority:** ⚠️ **MINOR**  
**Recommendation:** ✅ **ADOPT**

**What Changed:**
- `get_frame()` checks if thread is already running before initializing
- Prevents repeated initialization attempts

**Code Location (Pi):**
- `get_frame()` method, lines ~472-475

**Repository Status:**
- ❓ Current repo may already have this

**Adoption Notes:**
- Simple defensive programming
- Prevents race conditions

---

### Category 3: SHOULD NOT ADOPT ❌

These changes revert newer, better features or conflict with recent improvements.

#### 3.1 ROI Handling - Canvas-Based Approach

**Files:**
- `rio-webapp/templates/index.html`
- `rio-webapp/static/roi_selector.js`
- `controllers/camera.py` (`_handle_roi_set()` method)

**Priority:** ⚠️ **DO NOT ADOPT**  
**Recommendation:** ❌ **REJECT**

**What Changed (Pi Code):**
- Reverts to canvas-based ROI selection with coordinate conversion
- Removes slider-based ROI UI
- Uses old `roi_selector.js` instead of `roi_selector_simple.js`

**Why NOT Adopt:**
1. **Repository has newer, better approach** - Slider-based UI (recently added) is more reliable
2. **User explicitly mentioned** - ROI handling was recently changed, old approach is obsolete
3. **Canvas coordinate issues** - The Pi code's fixes for canvas coordinates were workarounds for a fundamentally flawed approach
4. **Browser compatibility** - Slider-based approach works better across browsers

**Repository Status:**
- ✅ Repository has slider-based ROI (`roi_selector_simple.js`)
- ✅ Better UI with sliders and numeric inputs
- ✅ No canvas coordinate conversion issues

**Recommendation:**
- **Keep repository's slider-based approach**
- Do NOT adopt Pi code's canvas-based ROI handling
- The Pi code's ROI fixes were workarounds, not solutions

---

#### 3.2 Removal of Hardware ROI Features

**Files:** 
- `controllers/camera.py`
- `drivers/camera/pi_camera_v2.py`
- `drivers/camera/mako_camera.py`

**Priority:** ⚠️ **DO NOT ADOPT**  
**Recommendation:** ❌ **REJECT**

**What Changed (Pi Code):**

1. **`controllers/camera.py`:**
   - Removed hardware ROI calls in `_handle_roi_set()` and `_handle_roi_clear()`
   - Removed validation and constraint handling

2. **`drivers/camera/pi_camera_v2.py`:**
   - Removed `set_roi_hardware()` method (~100 lines)
   - Removed `get_max_resolution()` method
   - Removed `get_roi_constraints()` method (~80 lines)
   - Removed `validate_and_snap_roi()` method (~50 lines)
   - Removed hardware ROI state tracking (`self.hardware_roi`, `self.sensor_size`)
   - Reverted `get_frame_roi()` to simple software cropping
   - **Total removed: ~226 lines of hardware ROI code**

3. **`drivers/camera/mako_camera.py`:**
   - Removed `set_roi_hardware()` method (~30 lines)
   - Removed `get_max_resolution()` method
   - Removed `get_roi_constraints()` method (~90 lines)
   - Reverted `get_frame_roi()` to simple software cropping
   - **Total removed: ~126 lines of hardware ROI code**

**Why NOT Adopt:**
1. **Hardware ROI is better** - Reduces Pi load, increases frame rate
2. **Recently added feature** - Part of recent improvements
3. **Works with multiple cameras** - Mako and Pi cameras both support it
4. **Performance benefit** - Hardware ROI is more efficient than software cropping
5. **Significant code removal** - ~350+ lines of well-implemented hardware ROI code removed

**Repository Status:**
- ✅ Repository has hardware ROI support in all camera drivers
- ✅ Repository calls hardware ROI in camera controller
- ✅ Better performance and frame rates
- ✅ Proper constraint handling for Mako cameras

**Recommendation:**
- **Keep repository's hardware ROI implementation**
- Do NOT adopt Pi code's removal of hardware ROI
- This was likely removed during troubleshooting but shouldn't be removed permanently
- The hardware ROI code in the repository is more complete and better implemented

---

#### 3.3 Removal of CAMERA_DISPLAY_FPS

**Files:** 
- `config.py`
- `controllers/camera.py`
- `rio-webapp/routes.py`

**Priority:** ⚠️ **DO NOT ADOPT**  
**Recommendation:** ❌ **REJECT**

**What Changed (Pi Code):**

1. **`config.py`:**
   - Removed `CAMERA_DISPLAY_FPS` configuration constant

2. **`controllers/camera.py`:**
   - Removed `display_fps` from camera controller
   - Removed `display_fps` from `cam_data`

3. **`rio-webapp/routes.py` (video route):**
   - Removed frame rate limiting logic
   - Removed `display_fps` usage
   - Changed from rate-limited generator to simple generator
   - **Note:** Also added CORS headers (see 4.4 for evaluation)

**Why NOT Adopt:**
1. **Useful for Pi load reduction** - Lower display FPS reduces CPU/network load
2. **Separate from capture FPS** - Allows high capture FPS with lower streaming FPS
3. **Performance optimization** - Important for Pi performance
4. **Reduces bandwidth** - Lower frame rate reduces network bandwidth usage

**Repository Status:**
- ✅ Repository has `CAMERA_DISPLAY_FPS = 10` in config.py
- ✅ Repository uses it in camera controller
- ✅ Repository implements frame rate limiting in video route

**Recommendation:**
- **Keep repository's display FPS feature**
- Do NOT adopt Pi code's removal
- This is a useful optimization that should be preserved
- The frame rate limiting in routes.py is important for Pi performance

---

### Category 4: NEEDS EVALUATION ⚠️

These changes may be good but need careful evaluation or may conflict with other features.

#### 4.1 CORS Headers Addition

**File:** `rio-webapp/routes.py`  
**Priority:** ⚠️ **EVALUATE**  
**Recommendation:** ⚠️ **EVALUATE** (May be useful)

**What Changed (Pi Code):**
- Added CORS headers to video stream response:
  - `Access-Control-Allow-Origin: *`
  - `Cache-Control: no-cache, no-store, must-revalidate`
  - `Pragma: no-cache`
  - `Expires: 0`

**Why Evaluate:**
- **May help with cross-origin issues** - If accessing video stream from different origin
- **Cache control** - Prevents browser caching of video stream (good for live video)
- **Security consideration** - `Access-Control-Allow-Origin: *` allows any origin (may be too permissive)

**Repository Status:**
- ❓ Current repo doesn't have CORS headers

**Recommendation:**
- **Consider adding cache control headers** - These are good for live video streams
- **Evaluate CORS headers** - Only add if actually needed, and consider being more restrictive than `*`
- **Test cross-origin access** - Verify if CORS is actually needed for your use case

---

#### 4.2 Exposure Mode Handling

**File:** `drivers/camera/pi_camera_legacy.py`  
**Priority:** ⚠️ **EVALUATE**  
**Recommendation:** ⚠️ **EVALUATE CAREFULLY**

**What Changed (Pi Code):**
- Sets exposure mode to "auto" for video streaming unless shutter speed explicitly set
- Only sets exposure_mode="off" when shutter speed is provided

**Why Evaluate:**
- May conflict with strobe-centric mode requirements (which need exposure_mode="off")
- Auto exposure might interfere with strobe timing
- Need to verify this doesn't break strobe synchronization

**Repository Status:**
- ❓ Current repo behavior needs review

**Recommendation:**
- **Test thoroughly with strobe-centric mode**
- May need conditional logic: "auto" for preview, "off" for strobe mode
- Don't adopt blindly - verify it doesn't break strobe timing

---

#### 4.3 Template/HTML Changes

**File:** `rio-webapp/templates/index.html`  
**Priority:** ⚠️ **EVALUATE SELECTIVELY**  
**Recommendation:** ⚠️ **ADOPT SELECTIVE FIXES ONLY**

**What Changed (Pi Code):**
- Fixed camera resolution initialization in JavaScript (dict access instead of method call)
- Added CSS for canvas layering (`pointer-events: none` on image, `z-index` on canvas)
- Canvas-based ROI handling (rejected - see 3.1)

**What to Adopt:**
- ✅ JavaScript camera resolution fix (if still needed with slider-based ROI)
- ✅ CSS canvas layering fixes (if canvas is still used for visualization)
- ❌ Canvas-based ROI handling (rejected)

**Recommendation:**
- **Adopt only the fixes that are still relevant**
- Since repo uses slider-based ROI, canvas fixes may not be needed
- Review if canvas is used at all in current repo

---

#### 4.4 Strobe Timing Command Handling

**File:** `controllers/camera.py`  
**Priority:** ⚠️ **EVALUATE**  
**Recommendation:** ⚠️ **EVALUATE**

**What Changed (Pi Code):**
- `CMD_TIMING` handler now passes `wait_ns` parameter to `set_timing()`
- Calls `strobe_cam.set_timing()` directly instead of `self.set_timing()`
- Removed automatic strobe enable from timing command

**Why Evaluate:**
- Different API - may need to reconcile with current implementation
- Removing automatic enable might be intentional (user controls it separately)
- Need to verify this doesn't break existing functionality

**Repository Status:**
- ❓ Current repo behavior needs review

**Recommendation:**
- **Review current timing command handler**
- Ensure API consistency
- Test strobe timing commands after adoption

---

## Code Bloat Analysis

**File Size Comparison:**

| File | Repository | Pi Code | Difference | Analysis |
|------|------------|---------|------------|----------|
| `strobe_cam.py` | 388 lines | 498 lines | +110 lines (+28%) | **Acceptable** - Most increase is dead time calculation (necessary) |
| `camera.py` | 982 lines | 951 lines | -31 lines (-3%) | **Good** - Slightly smaller, removed hardware ROI code |
| `pi_camera_legacy.py` | 426 lines | 425 lines | -1 line | **Minimal** - Essentially unchanged |
| `pi_camera_v2.py` | 616 lines | 390 lines | -226 lines (-37%) | **Removed hardware ROI** - Should NOT adopt |
| `mako_camera.py` | 515 lines | 294 lines | -221 lines (-43%) | **Removed hardware ROI** - Should NOT adopt |

**Assessment:**
- The increase in `strobe_cam.py` is justified - dead time calculation is critical functionality
- The code is well-structured and not "bloated" - additions are necessary fixes
- No unnecessary complexity was added during troubleshooting
- The large reductions in `pi_camera_v2.py` and `mako_camera.py` are due to removal of hardware ROI features that should be kept

---

## Implementation Priority

### Phase 1: Critical Fixes (Must Do First) ⚠️

1. ✅ Add hardware readback methods to camera abstraction layer
   - Add abstract methods to `BaseCamera`
   - Implement in `PiCameraLegacy` and `PiCameraV2`
   
2. ✅ Implement dead time calculation in strobe-centric mode
   - Add `_get_actual_framerate()` and `_get_actual_shutter_speed()` helpers
   - Add dead time calculation logic to `set_timing()` strobe-centric branch
   - Ensure correct order of operations

3. ✅ Fix conditional trigger mode configuration
   - Only call `set_trigger_mode()` in camera-centric mode
   - Add logging for skipped configuration in strobe-centric mode

### Phase 2: Important Improvements (Do Next)

4. ✅ Improve strobe driver error handling
   - Add safety checks for empty SPI responses
   - Balance strictness with robustness

5. ✅ Fix framerate clamping
   - Recalculate shutter speed when framerate is clamped

6. ✅ Improve strobe control UI state synchronization
   - Update UI state to match user intent
   - Ensure proper error logging

7. ✅ Add camera initialization error handling
   - Gracefully handle camera initialization failures
   - Prevent crashes during camera type changes

### Phase 3: Performance Fixes (Evaluate and Test)

8. ⚠️ Evaluate camera frame generation fixes
   - Test current repo implementation
   - Adopt Pi code fixes if needed
   - Verify doesn't conflict with other optimizations

9. ⚠️ Evaluate exposure mode handling
   - Test with strobe-centric mode
   - May need conditional logic
   - Don't break strobe synchronization

### Phase 4: Selective Template Fixes (If Still Needed)

10. ⚠️ Review template/HTML fixes
    - Only adopt fixes relevant to current UI (slider-based ROI)
    - May not need canvas fixes if canvas not used

---

## Testing Requirements

After adopting changes, test:

1. **Strobe-Centric Mode:**
   - ✅ Verify strobe timing synchronization with oscilloscope/logic analyzer
   - ✅ Test dead time calculation with various framerate/shutter combinations
   - ✅ Verify hardware readback returns accurate values

2. **Camera Functionality:**
   - ✅ Test camera feed displays correctly
   - ✅ Test frame generation performance
   - ✅ Test camera initialization error handling

3. **Hardware Compatibility:**
   - ✅ Test with old firmware (strobe-centric mode, no trigger mode command)
   - ✅ Test with new firmware (camera-centric mode, trigger mode command)
   - ✅ Test SPI communication robustness

4. **UI Functionality:**
   - ✅ Test strobe enable/disable
   - ✅ Test strobe timing commands
   - ✅ Verify UI state matches hardware state

---

## Conflicts with Repository Features

### Features to Preserve (Do NOT Adopt Pi Code Changes That Remove These):

1. ✅ **Slider-based ROI selection** - Keep repository's implementation
2. ✅ **Hardware ROI support** - Keep repository's implementation
3. ✅ **CAMERA_DISPLAY_FPS** - Keep repository's configuration
4. ✅ **Any other recent improvements** - Review before removing

### Merge Strategy:

1. **Adopt fixes that don't conflict** - Dead time calculation, hardware readback, error handling
2. **Keep repository's newer features** - ROI handling, hardware ROI, display FPS
3. **Reconcile differences carefully** - Test thoroughly after merging
4. **Document any conflicts** - Note why certain changes weren't adopted

---

## Complete List of Changed Files

### Files with Changes to ADOPT ✅

1. **`controllers/strobe_cam.py`** - Dead time calculation, hardware readback helpers, conditional trigger mode
2. **`drivers/camera/pi_camera_legacy.py`** - Hardware readback methods, frame generation fixes
3. **`controllers/camera.py`** - UI state synchronization, error handling improvements, camera thread initialization check
4. **`drivers/strobe.py`** - Error handling improvements, safety checks

### Files with Changes to REJECT ❌

5. **`controllers/camera.py`** - Removal of hardware ROI calls (partial - other changes should be adopted)
6. **`drivers/camera/pi_camera_v2.py`** - Removal of ~226 lines of hardware ROI code
7. **`drivers/camera/mako_camera.py`** - Removal of ~126 lines of hardware ROI code
8. **`config.py`** - Removal of CAMERA_DISPLAY_FPS constant
9. **`rio-webapp/templates/index.html`** - Canvas-based ROI UI (reverts to old approach)
10. **`rio-webapp/static/roi_selector.js`** - Canvas coordinate fixes (reverts to old approach)
11. **`rio-webapp/routes.py`** - Removal of display FPS frame rate limiting (but CORS headers may be useful - see 4.1)

### Files with Changes to EVALUATE ⚠️

12. **`rio-webapp/routes.py`** - CORS headers addition (may be useful)
13. **`drivers/camera/pi_camera_legacy.py`** - Exposure mode handling (may conflict with strobe mode)

**Note:** Some files appear in multiple categories because they have both changes to adopt and changes to reject.

---

## Summary of Recommendations

| Category | Count | Action |
|----------|-------|--------|
| ✅ **Must Adopt** | 3 | Critical fixes for strobe synchronization |
| ✅ **Should Adopt** | 6 | Important improvements for reliability/performance |
| ❌ **Do Not Adopt** | 3 major areas | Reverts newer, better features (hardware ROI in 3 files, display FPS in 3 files, slider-based ROI in 2 files) |
| ⚠️ **Evaluate** | 4 | Need careful evaluation/testing (exposure mode, template fixes, timing commands, CORS headers) |

**Overall Assessment:**
The Pi code contains essential fixes that must be adopted, but also includes some changes that should NOT be adopted because they revert recent improvements. The code is not significantly bloated - the increase in size is justified by necessary fixes.

**Key Principle:**
Adopt the fixes that solve real problems (dead time calculation, hardware readback, error handling) but preserve the repository's newer, better features (hardware ROI, slider-based ROI, display FPS optimization).
