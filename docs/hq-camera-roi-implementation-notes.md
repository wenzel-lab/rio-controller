# HQ Camera ROI Implementation Notes

## Official Documentation

According to Raspberry Pi documentation:
- HQ Camera (IMX477) supports hardware ROI via `--roi` parameter in `rpicam-apps`
- Format: `--roi x,y,width,height` where values are normalized (0.0-1.0)
- Example: `rpicam-hello --roi 0.25,0.25,0.5,0.5` (central 50% of image)
- Works on both 32-bit and 64-bit Raspberry Pi OS

## Our Implementation (picamera2)

We use `ScalerCrop` control in picamera2, which is the Python API equivalent:

```python
# Normalized coordinates (0.0-1.0)
norm_x = x / sensor_width
norm_y = y / sensor_height  
norm_w = width / sensor_width
norm_h = height / sensor_height

# Set via set_controls (when camera stopped)
cam.set_controls({"ScalerCrop": (norm_x, norm_y, norm_w, norm_h)})
```

## References from Codebase

The `hardware-modules/strobe-imaging/readme.md` mentions high-speed imaging approaches:
- References to 660 fps examples with Pi Camera V2
- Mentions varying image size vs. frame rate
- Links to examples showing ROI/resolution trade-offs

## HQ Camera Specifications

- **Sensor**: Sony IMX477
- **Max Resolution**: ~4056 × 3040 pixels
- **Hardware ROI**: Supported via ScalerCrop
- **Frame Rate Benefits**: Smaller ROI = higher frame rate

## Implementation Details

1. **Sensor Size Detection**: Queries `cam.sensor_modes` to find max resolution
2. **Normalization**: Converts pixel coordinates to normalized (0.0-1.0)
3. **ScalerCrop**: Sets hardware ROI at sensor level
4. **Automatic**: Hardware ROI set when ROI is selected via UI

## Testing Recommendations

1. Verify sensor size detection works correctly for HQ camera
2. Test that ScalerCrop actually reduces frame size (not just software crop)
3. Measure frame rate increase with smaller ROI
4. Compare with rpicam-apps `--roi` behavior for consistency

## Notes

- HQ Camera definitely supports hardware ROI (confirmed in official docs)
- Our implementation follows the same normalized coordinate approach as rpicam-apps
- ScalerCrop is the picamera2 equivalent of `--roi` in rpicam-apps

