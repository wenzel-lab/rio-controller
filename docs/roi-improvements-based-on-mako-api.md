# ROI Improvements Based on Mako Camera API

## Summary

After exploring the Mako camera API in depth, we've implemented a better ROI selection system that:

1. **Uses click-and-drag (standard approach)** instead of sliders - more intuitive
2. **Queries camera constraints dynamically** from Mako API
3. **Validates and snaps ROI** to camera-required increments
4. **Provides numeric inputs** for fine-tuning (not sliders)
5. **Handles coordinates properly** across browsers

## Key Insights from Mako API

### 1. Camera Constraints Are Queryable

The Mako camera exposes ROI constraints via Vimba features:
- **Min/Max values** for OffsetX, OffsetY, Width, Height
- **Increment values** - ROI must align to certain pixel boundaries (often 2 or 4 pixels)
- **Current values** - can query what the camera is currently set to

### 2. Click-and-Drag is Standard

Research shows that click-and-drag ROI selection is the standard approach in image processing applications (like Photoshop, ImageJ, etc.). It's more intuitive than sliders.

### 3. Sliders Are Not Necessary

Instead of sliders, we provide:
- **Click-and-drag** for primary selection (intuitive)
- **Numeric input fields** for precise fine-tuning (more accurate than sliders)
- **Automatic validation** against camera constraints

## Implementation Details

### New Methods in MakoCamera

1. **`get_roi_constraints()`**
   - Queries camera for min, max, increment, and current values
   - Returns structured constraints dictionary
   - Falls back to defaults if camera not available

2. **`validate_and_snap_roi(roi)`**
   - Validates ROI against camera constraints
   - Snaps values to required increments
   - Ensures ROI fits within sensor bounds
   - Returns validated ROI tuple

### Improved ROI Selector (`roi_selector_improved.js`)

**Features:**
- Click-and-drag selection (standard image processing approach)
- Resize by dragging corners/edges
- Move by dragging center
- Numeric input fields for precise adjustment
- Automatic constraint validation and snapping
- Proper coordinate handling (image coordinates, not canvas coordinates)
- Works consistently across browsers

**Key Improvements:**
1. **Coordinate System**: Uses `naturalWidth`/`naturalHeight` for actual image dimensions, not displayed size
2. **Constraint Validation**: Automatically snaps ROI to camera-required increments
3. **Browser Compatibility**: Proper coordinate conversion eliminates browser differences
4. **User Experience**: Click-and-drag is more intuitive than sliders

### Backend Integration

**Camera Controller (`camera.py`):**
- `_handle_roi_set()` now validates ROI if camera supports it
- `_handle_roi_get()` includes constraints in response
- ROI is automatically snapped to valid values before storage

## Usage

### For Users

1. **Primary Selection**: Click and drag on the camera image to select ROI
2. **Fine-Tuning**: Use numeric input fields for precise values
3. **Automatic Validation**: ROI is automatically snapped to camera constraints
4. **Visual Feedback**: Green rectangle shows selected region

### For Developers

```python
# Query camera constraints
constraints = mako_camera.get_roi_constraints()
# Returns: {
#   "offset_x": {"min": 0, "max": 640, "increment": 2, "current": 0},
#   "offset_y": {"min": 0, "max": 480, "increment": 2, "current": 0},
#   "width": {"min": 10, "max": 640, "increment": 2, "current": 640},
#   "height": {"min": 10, "max": 480, "increment": 2, "current": 480}
# }

# Validate and snap ROI
validated_roi = mako_camera.validate_and_snap_roi((100, 50, 200, 150))
# Automatically snaps to increments and validates bounds
```

## Benefits

1. **More Intuitive**: Click-and-drag is familiar to users
2. **More Accurate**: Numeric inputs provide precision
3. **Camera-Aware**: Automatically respects camera constraints
4. **Browser-Compatible**: Proper coordinate handling works everywhere
5. **Less Resource-Intensive**: No slider animations, simpler UI

## Comparison: Sliders vs Click-and-Drag

| Aspect | Sliders | Click-and-Drag |
|--------|---------|----------------|
| Intuitiveness | Medium | High (standard) |
| Precision | Low (hard to hit exact values) | High (numeric inputs) |
| Speed | Slow (multiple adjustments) | Fast (single drag) |
| Resource Usage | Higher (animations) | Lower (static) |
| Browser Issues | Possible | None (proper coordinates) |

## Next Steps

1. **Test on Pi**: Verify click-and-drag works on Pi browser
2. **Test Constraints**: Verify Mako camera constraint querying works
3. **UI Polish**: Add visual feedback for constraint snapping
4. **Documentation**: Update user guide with new ROI selection method

## Files Changed

- `software/drivers/camera/mako_camera.py` - Added constraint querying
- `software/rio-webapp/static/roi_selector_improved.js` - New improved selector
- `software/controllers/camera.py` - Added constraint validation
- `pi-deployment/` - Synced all changes

## References

- Mako Camera Technical Manual: ROI constraints and increments
- Vimba Python API: Feature querying (`get_range()`, `get_increment()`)
- Standard image processing practices: Click-and-drag ROI selection

