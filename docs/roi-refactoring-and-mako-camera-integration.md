# ROI Refactoring and Mako Camera Integration

## Overview

This document describes the refactoring of the Region of Interest (ROI) selection system to improve reliability across browsers, reduce Raspberry Pi load, and add support for Mako camera hardware ROI features.

## Problems Addressed

1. **Browser Coordinate Inconsistency**: Free-form canvas-based ROI selection had coordinate issues between Pi browser and Mac browser
2. **Pi Overload**: Displaying all frames at full resolution was overloading the Raspberry Pi
3. **Mako Camera Support**: Need to leverage Mako camera's native hardware ROI support for better performance
4. **Frame Rate Management**: Need to separate display FPS from capture FPS

## Changes Made

### 1. Mako Camera Hardware ROI Support

**File**: `software/drivers/camera/mako_camera.py`

Added support for hardware ROI using Vimba features:
- `OffsetX` and `OffsetY`: Set the ROI origin on the sensor
- `Width` and `Height`: Set the ROI dimensions

**New Methods**:
- `set_roi_hardware(roi)`: Sets hardware ROI on Mako camera using Vimba features
- `get_max_resolution()`: Gets maximum sensor resolution
- `_set_camera_offset_x()` and `_set_camera_offset_y()`: Internal methods to set ROI offsets

**Benefits**:
- Hardware ROI reduces data transfer and processing load
- Faster frame rates when using smaller ROIs
- More efficient than software cropping

**Usage**:
```python
# Set hardware ROI (changes camera global settings)
mako_camera.set_roi_hardware((x, y, width, height))

# Or via config
mako_camera.set_config({
    "OffsetX": x,
    "OffsetY": y,
    "Width": width,
    "Height": height
})
```

### 2. Slider-Based ROI Selector UI

**File**: `software/rio-webapp/static/roi_selector_sliders.js`

Replaced free-form canvas selection with slider/input-based UI:

**Features**:
- Number inputs for precise coordinate entry
- Range sliders for visual adjustment
- Visual overlay canvas (non-interactive, lighter weight)
- Consistent coordinate handling across browsers
- Lower resource usage than interactive canvas

**Benefits**:
- More reliable across different browsers (Pi browser vs Mac browser)
- Easier to use and more precise
- Reduced JavaScript processing load
- No coordinate scaling issues

### 3. Display Frame Rate Limiting

**Files**: 
- `software/config.py`: Added `CAMERA_DISPLAY_FPS = 10` constant
- `software/rio-webapp/routes.py`: Added frame rate limiting to video stream
- `software/controllers/camera.py`: Added `display_fps` tracking

**Implementation**:
- Display FPS defaults to 10 fps (configurable)
- Separate from capture FPS (30 fps for analysis)
- Reduces Pi load while maintaining full capture rate for droplet detection

**Benefits**:
- Significantly reduces Pi CPU/network load
- Still captures all frames for droplet analysis
- Better user experience with smoother display

### 4. HTML Template Updates

**File**: `software/rio-webapp/templates/index.html`

Updated to use slider-based ROI selector:
- Replaced canvas-based ROI selector with slider/input controls
- Added ROI configuration card with X, Y, Width, Height controls
- Maintains visual overlay for ROI preview

## Comparison with Flow-Platform Implementation

### Current Implementation (This Repository)

1. **ROI Selection**:
   - Slider/input-based UI (new)
   - Software cropping for all cameras
   - Hardware ROI support for Mako (new)

2. **Frame Rate**:
   - Separate display FPS (10 fps) and capture FPS (30 fps)
   - Frame rate limiting in video stream route

3. **Camera Abstraction**:
   - BaseCamera abstract class
   - Unified interface for Pi cameras and Mako
   - Config-based setup

### Flow-Platform Implementation (Reference)

Based on code comments, the flow-platform repository has:
- Tested Mako camera implementation with Vimba
- Similar camera abstraction layer
- Likely uses hardware ROI for Mako cameras
- May have different frame rate management

**Key Differences to Note**:
1. Our implementation adds slider-based UI for better browser compatibility
2. We've added explicit display FPS limiting to reduce Pi load
3. Hardware ROI support is now available but optional (can use software cropping for compatibility)

## Mako Camera ROI Details

### How Mako Camera Handles ROI

Mako cameras support hardware ROI through Vimba features:

1. **OffsetX/OffsetY**: Define the top-left corner of the ROI on the sensor
2. **Width/Height**: Define the ROI dimensions
3. **Constraints**: 
   - ROI must align to sensor-specific increments (usually 2 or 4 pixels)
   - Maximum ROI is sensor size
   - Setting ROI changes global camera settings

### ROI vs Resolution Reduction

- **Hardware ROI**: Camera only reads specified region (faster, less data)
- **Resolution Reduction**: Camera reads full sensor but outputs smaller size (more data, slower)

For Mako cameras, hardware ROI is preferred for performance.

### Frame Rate Impact

Smaller ROIs enable higher frame rates:
- Full sensor (640×480): ~550 fps max
- Reduced ROI (320×240): ~1000+ fps possible
- Very small ROI (160×120): Even higher rates

## Usage Instructions

### Setting ROI via UI

1. Navigate to Camera View tab
2. Use sliders or input fields to set:
   - X Position: Left edge of ROI
   - Y Position: Top edge of ROI
   - Width: ROI width in pixels
   - Height: ROI height in pixels
3. ROI is automatically saved and sent to server
4. Visual overlay shows selected region on camera feed

### Setting ROI Programmatically

```python
# Via WebSocket (from frontend)
socket.emit('roi', {
    cmd: 'set',
    parameters: {x: 100, y: 100, width: 400, height: 300}
});

# Via Python (backend)
camera.on_roi({
    'cmd': 'set',
    'parameters': {'x': 100, 'y': 100, 'width': 400, 'height': 300}
})
```

### Using Hardware ROI for Mako Camera

```python
# In camera driver
if isinstance(camera, MakoCamera):
    camera.set_roi_hardware((x, y, width, height))
```

## Configuration

### Display FPS

Default: 10 fps (defined in `config.py`)

To change:
```python
# In config.py
CAMERA_DISPLAY_FPS = 15  # Increase for smoother display (more Pi load)
```

Or via camera controller:
```python
camera.display_fps = 15
camera.cam_data["display_fps"] = 15
```

## Testing Notes

### Browser Compatibility

The slider-based approach should work consistently across:
- Raspberry Pi browser (Chromium-based)
- Mac Safari/Chrome
- Other modern browsers

### Coordinate Handling

- All coordinates are in image pixels (not canvas pixels)
- No scaling needed between browsers
- ROI is stored and transmitted in absolute pixel coordinates

### Performance

- Display FPS limiting reduces Pi CPU usage significantly
- Hardware ROI on Mako cameras reduces data transfer
- Slider-based UI reduces JavaScript processing load

## Future Improvements

1. **Auto-detect ROI constraints**: Query Mako camera for ROI increment requirements
2. **ROI presets**: Save/load common ROI configurations
3. **Visual feedback**: Show frame rate impact when changing ROI size
4. **Hardware ROI for Pi cameras**: Investigate if picamera2 supports hardware ROI

## References

- Mako Camera Technical Manual: ROI and frame rate specifications
- Vimba Python API: OffsetX, OffsetY, Width, Height features
- Flow-Platform Repository: Reference implementation for Mako camera integration

