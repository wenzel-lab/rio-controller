# Droplet Simulation Improvements
## Enhanced Realistic Droplet Generation

**Date:** December 10, 2025

---

## Issues Identified

1. **Aspect Ratio Too Strict**: Default `min_aspect_ratio: 1.5` filtered out round droplets (aspect ratio ~1.0)
2. **Simple Droplet Shapes**: Only perfect circles, no elliptical droplets
3. **Slow Movement**: Droplets moved too slowly (1-2 px/frame)
4. **No Collision Detection**: Droplets could overlap
5. **Motion Threshold Too High**: `min_motion: 2.0` pixels might filter out valid droplets

---

## Fixes Applied

### 1. Fixed Aspect Ratio Configuration

**File:** `droplet-detection/config.py`

**Changes:**
- `min_aspect_ratio`: `1.5` → `0.5` (allows round droplets ~1.0)
- `max_aspect_ratio`: `10.0` → `3.0` (allows some elliptical, but not too extreme)

**Impact:**
- Round droplets (aspect ratio ~1.0) are now detected
- Some elliptical droplets (1.2-2.0) are also allowed
- More realistic detection parameters

### 2. Lowered Motion Threshold

**File:** `droplet-detection/config.py`

**Changes:**
- `min_motion`: `2.0` → `0.5` pixels per frame

**Impact:**
- More droplets pass motion validation
- Better detection of slow-moving droplets

### 3. Enhanced Droplet Simulation

**File:** `simulation/camera_simulated.py`

**Major Improvements:**

#### a) Round and Elliptical Shapes
- **70% round droplets**: Aspect ratio 0.9-1.1
- **30% elliptical droplets**: Aspect ratio 1.2-2.0
- Uses `cv2.ellipse()` instead of `cv2.circle()` for realistic shapes

#### b) Faster Movement
- **Speed**: 3-8 pixels per frame (was 1-2)
- More dynamic, realistic flow behavior
- Random direction angles for varied movement

#### c) Collision Detection
- Droplets detect collisions with other droplets
- Velocity reflection on collision (with damping)
- Minimum spacing to prevent initial overlap
- Droplets "just touching" as requested

#### d) Better Visual Appearance
- High contrast: White droplets (255, 255, 255) on dark background (20, 20, 20)
- Subtle highlight for 3D effect
- More realistic appearance matching test datasets

#### e) Increased Droplet Count
- Default: `5` → `8` droplets per frame
- Better for testing detection algorithms
- Size range: `(10, 50)` → `(15, 45)` pixels (more realistic)

---

## Technical Details

### Collision Detection Algorithm

```python
# For each droplet, check distance to all other droplets
dist = sqrt((x1 - x2)² + (y1 - y2)²)
min_dist = radius1 + radius2 + 2  # Just touching (2px gap)

if dist < min_dist:
    # Collision: reflect velocity with damping
    velocity *= -0.8
```

### Ellipse Drawing

```python
# Calculate axes based on aspect ratio
if aspect_ratio >= 1.0:
    axes = (radius * aspect_ratio, radius)  # Horizontal ellipse
else:
    axes = (radius, radius / aspect_ratio)  # Vertical ellipse

cv2.ellipse(frame, center, axes, angle, 0, 360, color, -1)
```

### Initial Placement

- Minimum spacing: 100 pixels between droplet centers
- Prevents initial overlap
- Up to 50 attempts per droplet to find valid position
- Falls back gracefully if no position found

---

## Expected Results

### Before Fixes
- **Droplets detected**: ~2 per 581 frames (0.3% detection rate)
- **Issue**: Round droplets filtered out by aspect ratio
- **Issue**: Droplets too simple, not realistic

### After Fixes
- **Expected detection rate**: 50-80% of droplets should be detected
- **Round droplets**: Now detected (aspect ratio ~1.0 allowed)
- **Elliptical droplets**: Also detected (aspect ratio 1.2-2.0)
- **Better movement**: Faster, more dynamic
- **No overlaps**: Collision detection prevents overlapping

---

## Testing Recommendations

1. **Start Detection:**
   ```bash
   python main.py 5001
   ```

2. **Set Large ROI:**
   - Cover most of the frame to capture moving droplets
   - Droplets move quickly, so larger ROI = better capture

3. **Monitor Logs:**
   - Look for: `"Frame X: Y droplet(s) detected"`
   - Should see detections every few frames
   - If still seeing "No contours detected" or "all filtered out", check:
     - ROI covers droplet movement area
     - Background initialization complete (30 frames)

4. **Check Histograms:**
   - Should see data accumulating
   - Round droplets: aspect ratio ~1.0
   - Elliptical droplets: aspect ratio 1.2-2.0

---

## Configuration Adjustments

If detection is still low, try:

```python
# Via API or config file
{
    "min_area": 10,           # Lower minimum (default: 20)
    "max_area": 10000,       # Higher maximum (default: 5000)
    "min_aspect_ratio": 0.3, # More lenient (default: 0.5)
    "max_aspect_ratio": 4.0, # More lenient (default: 3.0)
    "min_motion": 0.1,       # Very low threshold (default: 0.5)
    "use_frame_diff": false, # Disable if too strict
}
```

---

## Files Modified

1. **`droplet-detection/config.py`**
   - Fixed aspect ratio defaults (0.5-3.0)
   - Lowered motion threshold (0.5 pixels)

2. **`simulation/camera_simulated.py`**
   - Complete rewrite of droplet generation
   - Added collision detection
   - Added elliptical shapes
   - Increased movement speed
   - Better visual appearance

3. **`droplet-detection/detector.py`**
   - Improved logging (INFO level for detections)
   - Better debugging information

---

## Summary

✅ **Fixed**: Aspect ratio filtering (now allows round droplets)  
✅ **Fixed**: Motion threshold (lowered for better detection)  
✅ **Enhanced**: Droplet simulation (realistic round/elliptical, collision detection, faster movement)  
✅ **Improved**: Visual appearance (high contrast, 3D effect)  
✅ **Increased**: Default droplet count (8 per frame)

**Status:** Ready for testing with improved simulation and detection parameters.
