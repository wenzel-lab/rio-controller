# Strobe-Centric Mode: Old vs New Implementation Comparison

## Purpose

This document compares the **old working implementation** of strobe-centric mode (found in `hardware-modules/strobe-imaging/strobe_python/pistrobecam.py`) with the **new implementation** (in `software/controllers/strobe_cam.py`) to identify differences, issues, and simplification opportunities.

## Executive Summary

**Critical Issue Found:** The new implementation is missing a critical timing adjustment that accounts for the "dead time" between camera frames. This adjustment is essential for proper synchronization in strobe-centric mode.

**Key Differences:**
1. **Missing dead time calculation** - Old code adjusts pre_padding_ns for inter-frame dead time, new code does not
2. **Camera abstraction layer** - New code uses abstraction layer instead of direct `picamera`, which may introduce differences
3. **Unnecessary complexity** - New code includes hardware trigger mode logic even in strobe-centric mode
4. **Trigger mode configuration** - New code calls `set_trigger_mode()` even when not needed for strobe-centric

---

## Detailed Comparison

### 1. Initialization (`__init__`)

#### Old Implementation (`hardware-modules/strobe-imaging/strobe_python/pistrobecam.py`)
```python
def __init__( self, port, reply_pause_s ):
    self.strobe = PiStrobe( port, reply_pause_s )
    self.camera = PiCamera()
    self.camera.awb_mode = 'auto'
    self.camera.exposure_mode = 'off'
```

**Characteristics:**
- Simple, direct initialization
- Direct `picamera.PiCamera()` instantiation
- Sets camera exposure mode to 'off' immediately
- No trigger mode configuration
- No GPIO setup (not needed for strobe-centric)

#### New Implementation (`software/controllers/strobe_cam.py`)
```python
def __init__(self, port, reply_pause_s, trigger_gpio_pin=18):
    # Determine control mode
    mode = STROBE_CONTROL_MODE.lower()
    if mode in (STROBE_CONTROL_MODE_STROBE_CENTRIC, ...):
        self.control_mode = STROBE_CONTROL_MODE_STROBE_CENTRIC
    else:
        self.control_mode = STROBE_CONTROL_MODE_CAMERA_CENTRIC
    self.hardware_trigger_mode = (self.control_mode == STROBE_CONTROL_MODE_CAMERA_CENTRIC)
    
    # Initialize strobe
    self.strobe = PiStrobe(port, reply_pause_s)
    
    # Initialize camera using abstraction layer
    self.camera = create_camera()
    self.camera.set_config({"Width": 640, "Height": 480, "FrameRate": 30})
    
    # GPIO setup (only for hardware trigger mode)
    if self.hardware_trigger_mode:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_gpio_pin, GPIO.OUT)
        GPIO.output(self.trigger_gpio_pin, GPIO.LOW)
    
    # Configure strobe trigger mode
    self.strobe.set_trigger_mode(self.hardware_trigger_mode)  # ⚠️ CALLED EVEN IN STROBE-CENTRIC
    
    # Set frame callback (only for hardware trigger mode)
    if self.camera and self.hardware_trigger_mode:
        self.camera.set_frame_callback(self.frame_callback_trigger)
```

**Characteristics:**
- Mode detection and conditional logic
- Camera abstraction layer (`create_camera()`)
- GPIO setup (conditional, but still processed)
- **Calls `set_trigger_mode()` even for strobe-centric mode** ⚠️
- Frame callback setup (conditional, but logic is present)

**Issues:**
1. **Unnecessary `set_trigger_mode()` call**: The new code calls `self.strobe.set_trigger_mode(self.hardware_trigger_mode)` even when in strobe-centric mode. This sends SPI command `PACKET_TYPE_SET_TRIGGER_MODE` (type 5) to the PIC, which may not be supported by old firmware. This could cause failures or unexpected behavior.
2. **Complex initialization path**: Even in strobe-centric mode, the code goes through all the conditional checks and mode determination logic.

---

### 2. `set_timing()` Method - **CRITICAL DIFFERENCE**

This is the **most important difference** and likely the root cause of synchronization issues.

#### Old Implementation
```python
def set_timing( self, pre_padding_ns, strobe_period_ns, post_padding_ns ):
    # Step 1: Calculate total exposure time
    shutter_speed_us = int( ( strobe_period_ns + pre_padding_ns + post_padding_ns ) / 1000 )
    
    # Step 2: Calculate framerate from shutter speed
    framerate = 1000000 / shutter_speed_us
    if ( framerate > 60 ):
        framerate = 60
    
    # Step 3: Set camera framerate and shutter speed
    self.camera.framerate = framerate
    self.camera.shutter_speed = shutter_speed_us
    
    # Step 4: Calculate inter-frame period
    frame_rate_period_us = int( 1000000 / float( self.camera.framerate ) )
    
    # Step 5: ⚠️ CRITICAL - Calculate dead time after frame
    strobe_pre_wait_us = frame_rate_period_us - self.camera.shutter_speed
    
    # Step 6: ⚠️ CRITICAL - Adjust pre_padding to include dead time
    pre_padding_ns = pre_padding_ns + ( 1000 * strobe_pre_wait_us )
    
    # Step 7: Set strobe timing with adjusted pre_padding
    valid, self.strobe_wait_ns, self.strobe_period_ns = self.strobe.set_timing( pre_padding_ns, strobe_period_ns )
    
    self.framerate_set = framerate
    return valid
```

**Key Point:** The old code **adds the dead time** (time between frame capture completion and next frame start) to the pre_padding before sending it to the PIC. This ensures the strobe fires at the correct time relative to the **next frame start**, not the current frame end.

**Why this matters:**
- Camera has a shutter speed (exposure time)
- Camera has a framerate (inter-frame period)
- Dead time = inter-frame period - shutter speed
- Strobe needs to account for this dead time to synchronize with the **start** of the next frame

#### New Implementation
```python
def set_timing(self, pre_padding_ns: int, strobe_period_ns: int, post_padding_ns: int) -> bool:
    try:
        # Step 1: Set strobe timing (without dead time adjustment!)
        if not self._set_strobe_timing(pre_padding_ns, strobe_period_ns):
            return False
        
        # Step 2: Calculate camera timing
        framerate, shutter_speed_us = self._calculate_camera_timing(
            strobe_period_ns, pre_padding_ns, post_padding_ns
        )
        
        # Step 3: Update camera config
        if not self._update_camera_config(framerate, shutter_speed_us):
            return False
        
        # Step 4: Ensure camera started and strobe enabled
        if not self._ensure_camera_started():
            return False
        
        self.framerate_set = framerate
        return True
    except Exception as e:
        logger.error(f"Error in set_timing: {e}")
        return False

def _set_strobe_timing(self, pre_padding_ns: int, strobe_period_ns: int) -> bool:
    """Set strobe timing on hardware."""
    wait_ns = pre_padding_ns  # ⚠️ NO ADJUSTMENT FOR DEAD TIME!
    valid, self.strobe_wait_ns, self.strobe_period_ns = self.strobe.set_timing(
        wait_ns, strobe_period_ns
    )
    return cast(bool, valid)

def _calculate_camera_timing(self, strobe_period_ns: int, pre_padding_ns: int, post_padding_ns: int) -> tuple[int, int]:
    """Calculate camera framerate and shutter speed from strobe timing."""
    total_exposure_ns = strobe_period_ns + pre_padding_ns + post_padding_ns
    shutter_speed_us = int(total_exposure_ns / NS_TO_US)
    framerate = int(1000000 / shutter_speed_us)
    
    if framerate > MAX_FRAMERATE:
        framerate = MAX_FRAMERATE
    
    return framerate, shutter_speed_us
```

**Issues:**
1. **MISSING DEAD TIME CALCULATION**: The new code does NOT calculate or add the dead time to pre_padding_ns. This is a **critical bug**.
2. **Order of operations**: The new code sets strobe timing BEFORE setting camera timing, but it needs the camera's actual framerate/shutter to calculate dead time. This creates a chicken-and-egg problem.
3. **No access to actual camera values**: The new code calculates framerate and shutter, but never reads back the **actual** values from the camera (which may differ due to hardware limitations). The old code reads `self.camera.framerate` and `self.camera.shutter_speed` after setting them.

---

### 3. Camera Configuration

#### Old Implementation
```python
# Direct picamera access
self.camera.framerate = framerate
self.camera.shutter_speed = shutter_speed_us
# Then reads back actual values:
frame_rate_period_us = int( 1000000 / float( self.camera.framerate ) )
# Uses actual shutter_speed from camera
strobe_pre_wait_us = frame_rate_period_us - self.camera.shutter_speed
```

**Characteristics:**
- Direct property access
- Reads back actual values after setting
- Uses actual hardware values for calculations

#### New Implementation
```python
def _update_camera_config(self, framerate: int, shutter_speed_us: int) -> bool:
    if self.camera is None:
        return False
    try:
        self.camera.set_config({"FrameRate": framerate, "ShutterSpeed": shutter_speed_us})
        return True
    except Exception as e:
        logger.error(f"Error setting camera config: {e}")
        return False
```

**Characteristics:**
- Uses abstraction layer `set_config()`
- Does not read back actual values
- Assumes config values are applied exactly as specified

**Issues:**
1. **No verification**: The new code doesn't verify that the camera actually accepted the framerate/shutter values. Camera hardware may round or clamp these values.
2. **Can't use actual values**: Since the new code doesn't read back actual values, it can't use them in dead time calculations (even if that code were added).

---

### 4. Camera Exposure Mode

#### Old Implementation
```python
self.camera.exposure_mode = 'off'  # Set in __init__
```

#### New Implementation
- **Not explicitly set** in the new code
- May be set elsewhere, but not in `strobe_cam.py`

**Issue:**
- Exposure mode 'off' is critical for strobe-centric mode to work properly. If the camera is using auto-exposure, it will interfere with the strobe timing.

---

### 5. Strobe Enable

#### Old Implementation
```python
# In set_timing():
#        self.strobe.set_enable( True )  # Commented out

# In close():
self.strobe.set_enable( False )
self.strobe.set_hold( False )
```

**Characteristics:**
- Strobe enable is NOT automatically called in `set_timing()`
- Must be enabled separately (probably by the calling code)

#### New Implementation
```python
def _ensure_camera_started(self) -> bool:
    # ...
    try:
        self.strobe.set_enable(True)  # ⚠️ Automatically enables strobe
    except Exception as e:
        logger.error(f"Error enabling strobe: {e}")
        return False
```

**Characteristics:**
- Automatically enables strobe when timing is set
- Part of the `set_timing()` flow

**Issue:**
- This behavioral difference may cause the strobe to be enabled at unexpected times or interfere with the calling code's control flow.

---

### 6. Error Handling

#### Old Implementation
```python
# Minimal error handling
# Returns True/False from set_timing()
# No exception handling
```

#### New Implementation
```python
try:
    # ... timing logic
except Exception as e:
    logger.error(f"Error in set_timing: {e}")
    return False
```

**Characteristics:**
- More robust error handling
- Logging of errors
- Graceful degradation

**Assessment:**
- This is an improvement, but the underlying logic issues must be fixed first.

---

## Summary of Issues

### Critical Issues (Must Fix)

1. **Missing Dead Time Calculation** ⚠️ **CRITICAL**
   - **Location**: `strobe_cam.py`, `set_timing()` method
   - **Problem**: New code doesn't calculate or add dead time to pre_padding_ns
   - **Impact**: Strobe will fire at wrong time, causing synchronization failures
   - **Fix**: Add dead time calculation similar to old code:
     ```python
     # After setting camera config, read back actual values
     actual_framerate = self.camera.get_config().get("FrameRate")
     actual_shutter_speed_us = self.camera.get_config().get("ShutterSpeed")
     
     # Calculate dead time
     frame_rate_period_us = int(1000000 / float(actual_framerate))
     dead_time_us = frame_rate_period_us - actual_shutter_speed_us
     
     # Adjust pre_padding
     adjusted_pre_padding_ns = pre_padding_ns + (dead_time_us * 1000)
     
     # Re-set strobe timing with adjusted value
     self.strobe.set_timing(adjusted_pre_padding_ns, strobe_period_ns)
     ```

2. **Unnecessary `set_trigger_mode()` Call** ⚠️ **CRITICAL**
   - **Location**: `strobe_cam.py`, `__init__()` method, line ~161
   - **Problem**: Calls `self.strobe.set_trigger_mode()` even in strobe-centric mode
   - **Impact**: May cause SPI command failures with old firmware that doesn't support trigger mode command
   - **Fix**: Only call `set_trigger_mode()` when `hardware_trigger_mode == True`:
     ```python
     # Configure strobe trigger mode based on control mode
     if self.hardware_trigger_mode:  # Only for camera-centric mode
         try:
             self.strobe.set_trigger_mode(True)
             logger.debug("Strobe configured for hardware trigger mode")
         except Exception as e:
             logger.error(f"Error configuring strobe trigger mode: {e}")
             raise
     ```

3. **Camera Exposure Mode Not Set**
   - **Location**: `strobe_cam.py`, `__init__()` or camera initialization
   - **Problem**: Exposure mode is not explicitly set to 'off'
   - **Impact**: Camera may use auto-exposure, interfering with strobe timing
   - **Fix**: Set exposure mode when initializing camera:
     ```python
     if self.camera:
         self.camera.set_config({"ExposureMode": "off"})  # Or equivalent in abstraction
     ```

### Moderate Issues

4. **Order of Operations in `set_timing()`**
   - **Location**: `strobe_cam.py`, `set_timing()` method
   - **Problem**: Strobe timing is set before camera timing, but dead time calculation needs actual camera values
   - **Impact**: Can't calculate dead time correctly even if code is added
   - **Fix**: Reorder to:
     1. Set camera config
     2. Read back actual values
     3. Calculate dead time
     4. Adjust pre_padding
     5. Set strobe timing

5. **No Verification of Camera Config Values**
   - **Location**: `strobe_cam.py`, `_update_camera_config()`
   - **Problem**: Doesn't read back actual values after setting
   - **Impact**: Calculations use theoretical values instead of actual hardware values
   - **Fix**: Read back config after setting and use actual values

6. **Automatic Strobe Enable**
   - **Location**: `strobe_cam.py`, `_ensure_camera_started()`
   - **Problem**: Automatically enables strobe, different from old behavior
   - **Impact**: May interfere with calling code's control flow
   - **Fix**: Consider making strobe enable explicit or configurable

### Simplification Opportunities

7. **Remove Hardware Trigger Logic from Strobe-Centric Path**
   - **Location**: Throughout `strobe_cam.py`
   - **Suggestion**: When in strobe-centric mode, skip all hardware trigger initialization:
     - Don't set up GPIO
     - Don't set frame callbacks
     - Don't call `set_trigger_mode()`
   - **Benefit**: Simpler code path, fewer potential failure points

8. **Separate Classes or Methods for Each Mode**
   - **Suggestion**: Consider having separate `_set_timing_strobe_centric()` and `_set_timing_camera_centric()` methods
   - **Benefit**: Clearer logic, easier to maintain, less conditional complexity

9. **Direct Camera Property Access (If Possible)**
   - **Suggestion**: If the abstraction layer allows, consider reading back actual framerate/shutter directly rather than using config dictionary
   - **Benefit**: More reliable, matches old implementation pattern

---

## Testing Recommendations

### Test 1: Verify Dead Time Calculation
1. Set strobe timing with known values
2. Verify camera framerate and shutter speed are set correctly
3. Calculate expected dead time manually
4. Verify that pre_padding sent to PIC includes dead time adjustment
5. Verify strobe fires at correct time relative to frame start

### Test 2: Verify Trigger Mode Command
1. Run in strobe-centric mode with old firmware
2. Check SPI communication logs
3. Verify `PACKET_TYPE_SET_TRIGGER_MODE` (type 5) is NOT sent
4. Verify no SPI errors or timeouts

### Test 3: Verify Exposure Mode
1. Check camera config after initialization
2. Verify exposure mode is set to 'off' (or equivalent)
3. Verify camera doesn't auto-adjust exposure

### Test 4: Compare Timing with Old Implementation
1. Run old implementation with same timing parameters
2. Run new implementation with same parameters
3. Compare actual strobe timing using oscilloscope or similar
4. Verify synchronization is identical

### Test 5: Verify Camera Config Readback
1. Set camera framerate to 30 FPS
2. Read back actual framerate from camera
3. Verify it matches (or is close to) 30 FPS
4. Repeat for shutter speed
5. Use actual values in calculations

---

## Implementation Priority

1. **Priority 1 (Critical - Fix Immediately)**:
   - Add dead time calculation to `set_timing()`
   - Remove `set_trigger_mode()` call for strobe-centric mode
   - Set camera exposure mode to 'off'

2. **Priority 2 (Important - Fix Soon)**:
   - Reorder operations in `set_timing()` to set camera first
   - Add config readback and use actual values
   - Verify calculations match old implementation

3. **Priority 3 (Nice to Have - Consider Later)**:
   - Simplify code by separating strobe-centric and camera-centric paths
   - Consider separate methods for each mode
   - Improve error handling and logging

---

## Notes

- The old implementation in `hardware-modules/strobe-imaging/strobe_python/pistrobecam.py` is the **reference implementation** that was known to work
- The camera abstraction layer may introduce differences - need to verify it supports reading back actual config values
- The PIC firmware version matters - old firmware may not support trigger mode command
- Testing should be done on actual hardware with oscilloscope/logic analyzer to verify timing

---

## Additional Findings

### Camera Abstraction Layer Analysis

After reviewing `pi_camera_legacy.py`:

1. **Exposure Mode**: ✅ **Correctly Set**
   - Exposure mode IS set to 'off' in `start()` method (line 75)
   - Also set in `set_config()` method (line 202)
   - This matches the old implementation

2. **Config Readback**: ⚠️ **LIMITATION FOUND**
   - `set_config()` updates the internal `self.config` dictionary
   - It does NOT read back actual values from `self.cam.framerate` and `self.cam.shutter_speed`
   - The old code reads back actual values: `self.camera.framerate` and `self.camera.shutter_speed`
   - **Impact**: Cannot use actual hardware values for dead time calculation
   - **Fix Needed**: Add methods to read back actual framerate and shutter speed from camera hardware

3. **Direct Property Access**: ⚠️ **NOT AVAILABLE**
   - The abstraction layer uses `set_config()` instead of direct property access
   - Old code used: `self.camera.framerate = framerate` then `self.camera.framerate` (readback)
   - New code uses: `self.camera.set_config({"FrameRate": framerate})` but no readback
   - **Solution**: Need to add getter methods or read from `self.cam` directly in `PiCameraLegacy`

### Recommended Fix for Config Readback

Add methods to `PiCameraLegacy` to read back actual values:

```python
def get_actual_framerate(self) -> float:
    """Get actual framerate from camera hardware."""
    if self.cam is None:
        return self.config.get("FrameRate", 30)
    return float(self.cam.framerate)

def get_actual_shutter_speed(self) -> int:
    """Get actual shutter speed from camera hardware (microseconds)."""
    if self.cam is None:
        return self.config.get("ShutterSpeed", 10000)
    return int(self.cam.shutter_speed)
```

Then in `strobe_cam.py`, use these methods after setting config to get actual values for dead time calculation.

## Questions to Resolve

1. ✅ **Does the camera abstraction layer support reading back actual framerate and shutter speed values?**
   - **Answer**: NO - Currently `set_config()` does not read back actual values. Need to add getter methods.

2. **What happens if `set_trigger_mode()` is called with old firmware that doesn't support that SPI command?**
   - **Action**: Test this on Pi with old firmware, check SPI communication logs for errors

3. ✅ **How is exposure mode handled in the camera abstraction layer?**
   - **Answer**: Exposure mode IS set to 'off' in `start()` and `set_config()` methods. This is correct.

4. **Should strobe enable be automatic or explicit?**
   - **Action**: Review calling code to determine expected behavior

5. **Are there any other differences in how `picamera` vs the abstraction layer handle timing?**
   - **Action**: Test timing accuracy with oscilloscope/logic analyzer
