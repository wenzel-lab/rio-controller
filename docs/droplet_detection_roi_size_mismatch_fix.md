# Droplet Detection ROI Size Mismatch Fix
## Background Size Mismatch Error Resolution

**Date:** December 2025

---

## Issue

**Error:**
```
cv2.error: OpenCV(4.12.0) ... error: (-209:Sizes of input arguments do not match) 
The operation is neither 'array op array' (where arrays have the same size and the same number of channels), 
nor 'array op scalar', nor 'scalar op array' in function 'arithm_op'
```

**Location:** `preprocessor.py`, line 98: `cv2.absdiff(gray, self.background)`

**Root Cause:**
When the ROI (Region of Interest) changes during detection, the background model was initialized with frames of one size, but new frames arrive with a different size. When `cv2.absdiff()` tries to subtract the old-sized background from the new-sized frame, OpenCV throws a size mismatch error.

**Scenario:**
1. Detection starts with ROI size A (e.g., 366×381)
2. Background is initialized with frames of size A
3. User changes ROI to size B (e.g., 664×493)
4. New frames arrive with size B
5. `cv2.absdiff(gray, self.background)` fails because sizes don't match

---

## Solution

### 1. Track Background Shape

Added `background_shape` attribute to track the size of frames used for background initialization:

```python
def __init__(self, config: DropletDetectionConfig):
    # ...
    self.background_shape: Optional[tuple] = None  # Track background size
```

### 2. Detect Size Changes During Initialization

Check if frame size changed when collecting background frames:

```python
def initialize_background(self, frame: np.ndarray) -> None:
    if self.config.background_method == "static":
        gray = ensure_grayscale(frame)
        
        # Check if frame size changed (ROI changed)
        current_shape = gray.shape[:2]  # (height, width)
        if self.background_shape is not None and self.background_shape != current_shape:
            logger.warning(f"Frame size changed from {self.background_shape} to {current_shape}, resetting background")
            self.reset_background()
        
        # Store shape for future comparisons
        if self.background_shape is None:
            self.background_shape = current_shape
        # ... rest of initialization
```

### 3. Validate Size Before Background Subtraction

Check that background and frame sizes match before performing subtraction:

```python
# 2. Background correction
if self.config.background_method == "static":
    if not self.background_initialized:
        # Still collecting background frames
        self.initialize_background(frame)
        return np.zeros_like(gray, dtype=np.uint8)

    # Check if background size matches current frame size
    if self.background is not None:
        if self.background.shape != gray.shape:
            logger.warning(f"Background shape {self.background.shape} doesn't match frame shape {gray.shape}, resetting")
            self.reset_background()
            self.initialize_background(frame)
            return np.zeros_like(gray, dtype=np.uint8)

    # Static background subtraction
    if self.background is not None:
        gray_corr = cv2.absdiff(gray, self.background)
    else:
        # Background not ready yet
        return np.zeros_like(gray, dtype=np.uint8)
```

### 4. Reset Background Shape on Reset

Clear the shape tracking when background is reset:

```python
def reset_background(self) -> None:
    """Reset background model (for re-initialization)."""
    self.background = None
    self.background_frames.clear()
    self.background_initialized = False
    self.background_shape = None  # Clear shape tracking
    logger.debug("Background model reset")
```

---

## Behavior After Fix

### When ROI Changes During Detection:

1. **Size Mismatch Detected:**
   - Preprocessor detects that `gray.shape != self.background.shape`
   - Logs warning: `"Background shape (h1, w1) doesn't match frame shape (h2, w2), resetting"`

2. **Background Reset:**
   - Background model is cleared
   - Background frames deque is cleared
   - `background_initialized` set to `False`
   - `background_shape` set to `None`

3. **Reinitialization:**
   - New frame is used to start background collection
   - `background_shape` is set to new frame size
   - Background collection begins again (requires `background_frames` frames)

4. **Graceful Handling:**
   - Frame that triggered reset returns empty mask (no droplets detected)
   - Subsequent frames continue background initialization
   - Once enough frames collected, background is computed and detection resumes

### Expected Log Messages:

```
WARNING - Background shape (381, 366) doesn't match frame shape (493, 664), resetting
DEBUG - Background model reset
INFO - Background initialized with 30 frames, shape: (493, 664)
```

---

## Files Modified

1. **`droplet-detection/preprocessor.py`**
   - Added `background_shape` attribute
   - Added size checking in `initialize_background()`
   - Added size validation before `cv2.absdiff()`
   - Updated `reset_background()` to clear shape

---

## Testing

### Test Case 1: ROI Change During Detection

1. Start detection with ROI size A
2. Wait for background initialization (30 frames)
3. Verify detection is working
4. Change ROI to size B
5. **Expected:** 
   - Warning logged about size mismatch
   - Background resets
   - Detection pauses briefly while background reinitializes
   - Detection resumes with new ROI size

### Test Case 2: Multiple ROI Changes

1. Start detection
2. Change ROI multiple times rapidly
3. **Expected:**
   - Each size change triggers reset
   - Background reinitializes for final ROI size
   - No crashes or repeated errors

### Test Case 3: ROI Change During Background Collection

1. Start detection (background collecting frames)
2. Change ROI before 30 frames collected
3. **Expected:**
   - Size change detected during collection
   - Background resets
   - Collection restarts with new size

---

## Impact

✅ **Fixed:** Size mismatch errors no longer crash detection  
✅ **Robust:** Handles ROI changes gracefully  
✅ **Automatic:** No user intervention required  
✅ **Logged:** Clear warnings when size changes detected  

**Trade-off:** When ROI changes, detection pauses briefly (30 frames) while background reinitializes. This is expected behavior for accurate background subtraction.

---

## Related Issues

- This fix handles dynamic ROI changes during detection
- Background reinitialization takes ~30 frames (configurable via `background_frames`)
- For best performance, avoid changing ROI frequently during detection

---

**Last Updated:** December 2025
