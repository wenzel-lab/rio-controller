# Pi Camera Hardware ROI Support

## Summary

Both Pi Camera V2 and HQ Camera now support hardware ROI, similar to Mako camera.

## Implementation

### Pi Camera V2 (64-bit, picamera2)
- **Method**: Uses `ScalerCrop` control in picamera2
- **Coordinates**: Converts pixel coordinates to normalized (0.0-1.0) for ScalerCrop
- **Benefits**: Sensor-level cropping, reduces data processing

### Pi Camera Legacy (32-bit, picamera)
- **Method**: Uses `crop` property (already supported)
- **Coordinates**: Converts pixel coordinates to normalized (0.0-1.0) for crop
- **Benefits**: Hardware-level cropping via picamera library

## How It Works

1. **User sets ROI** via sliders/numeric inputs
2. **Backend validates** ROI against camera constraints
3. **Hardware ROI is set**:
   - **picamera2**: `set_controls({"ScalerCrop": (norm_x, norm_y, norm_w, norm_h)})`
   - **picamera**: `cam.crop = (norm_x, norm_y, norm_w, norm_h)`
4. **Camera captures** only ROI region
5. **Frame rate increases** with smaller ROI

## Methods Added

All Pi camera classes now have:
- `set_roi_hardware(roi)` - Set hardware ROI
- `get_max_resolution()` - Get sensor max resolution
- `get_roi_constraints()` - Get ROI constraints (min, max, increment)
- `validate_and_snap_roi(roi)` - Validate and snap ROI to constraints

## Benefits

1. **Reduced Pi load**: Camera only captures ROI region
2. **Increased frame rate**: Smaller ROI = higher frame rate
3. **Consistent API**: Same interface as Mako camera
4. **Automatic**: Hardware ROI set automatically when ROI is selected

## Camera Support Matrix

| Camera | Hardware ROI | Method | Status |
|--------|--------------|--------|--------|
| Mako | ✅ Yes | OffsetX/OffsetY/Width/Height | ✅ Implemented |
| Pi V2 (64-bit) | ✅ Yes | ScalerCrop | ✅ Implemented |
| Pi HQ (64-bit) | ✅ Yes | ScalerCrop | ✅ Implemented |
| Pi Legacy (32-bit) | ✅ Yes | crop property | ✅ Implemented |

## Notes

- HQ Camera definitely supports hardware ROI (IMX477 sensor)
- V2 Camera (IMX219) may have limitations, but picamera2 supports it
- All cameras use normalized coordinates (0.0-1.0) internally
- Hardware ROI is set automatically when ROI is selected via UI

