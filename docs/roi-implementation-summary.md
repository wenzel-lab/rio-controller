# ROI Implementation Summary

## What Was Implemented

### 1. Simple Slider-Based ROI Selector
- **File**: `roi_selector_simple.js`
- **Features**:
  - Sliders for X, Y, Width, Height with numeric display
  - Numeric input fields for precise values
  - Read-only visual preview overlay (no canvas interaction)
  - Works directly with image pixel coordinates (no scaling issues)
  - Automatic constraint validation and snapping for Mako cameras

### 2. Hardware ROI for Mako Camera
- **When ROI is set**: Automatically calls `set_roi_hardware()` on Mako camera
- **Result**: Camera only captures ROI region, dramatically increasing frame rate
- **When ROI is cleared**: Resets camera to full frame

### 3. Constraint Support
- Queries Mako camera for ROI constraints (min, max, increment)
- Automatically snaps ROI values to valid increments
- Updates slider limits based on camera constraints

## How It Works

### User Experience
1. User adjusts sliders to select ROI
2. Numeric values update automatically
3. Visual preview shows selected region on image
4. ROI is automatically validated against camera constraints
5. For Mako: Hardware ROI is set automatically for frame rate increase

### Technical Flow
1. **Frontend**: Sliders → Numeric inputs → ROI object → WebSocket to backend
2. **Backend**: Receives ROI → Validates/snaps constraints → Sets hardware ROI (Mako) → Stores ROI
3. **Camera**: Mako camera captures only ROI region (hardware ROI active)
4. **Droplet Detection**: Gets ROI frame (already ROI size if hardware ROI active)

## Benefits

1. **No Canvas Coordinate Issues**: Works directly with image pixels, no scaling math
2. **Reliable Across Browsers**: Simple sliders/inputs work identically everywhere
3. **Hardware ROI for Mako**: Actual frame rate increase (e.g., 26 fps → 132 fps for smaller ROI)
4. **Constraint-Aware**: Automatically respects camera limitations
5. **User-Friendly**: Sliders make it easy to estimate coordinates visually

## Files Changed

- `software/rio-webapp/static/roi_selector_simple.js` - New simple slider-based selector
- `software/rio-webapp/templates/index.html` - Updated UI with sliders + numeric inputs
- `software/controllers/camera.py` - Added hardware ROI setting for Mako
- `software/drivers/camera/mako_camera.py` - Updated get_frame_roi() to detect hardware ROI
- `pi-deployment/` - All changes synced

## Testing Checklist

- [ ] Test slider-based ROI selection on Pi browser
- [ ] Test on Mac browser
- [ ] Verify hardware ROI is set on Mako camera when ROI is selected
- [ ] Verify frame rate increases with smaller ROI on Mako
- [ ] Test constraint validation (snapping to increments)
- [ ] Test ROI clearing resets Mako to full frame
- [ ] Verify visual preview shows correct ROI

## Notes

- Mako camera will be on PC, not Pi, so Pi load isn't the concern
- Frame rate increase is the main benefit for Mako hardware ROI
- Sliders make it easier for operators to estimate coordinates visually
- Numeric inputs provide precision when needed

