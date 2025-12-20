# ROI Analysis: Understanding Hardware ROI and What Actually Works

## What is Hardware ROI?

**Hardware ROI** means the camera sensor itself only reads a specific region, reducing:
- Data transfer from sensor to processor
- Memory usage
- Processing load
- Network bandwidth (for streaming)

**Software ROI** (what we currently do) means:
- Camera captures full frame (e.g., 1024×768)
- We crop in software after capture
- Still processes full frame data
- Doesn't reduce Pi load

## Current Implementation Reality

Looking at the code:

1. **Camera captures**: Full frame at `display_resolution` (e.g., 1024×768)
2. **For droplet detection**: Calls `get_frame_roi()` which does **software cropping**
   ```python
   # From mako_camera.py get_frame_roi():
   frame = self.get_frame_array()  # Gets FULL frame
   roi_frame = frame[y : y + height, x : x + width]  # Crops in software
   ```
3. **Result**: We're still capturing and processing full resolution, just throwing away pixels

**This doesn't reduce Pi load at all!**

## What Mako Camera Actually Supports

Based on research:
- **Mako cameras DO support arbitrary ROI** via OffsetX, OffsetY, Width, Height
- **Not just centered zoom** - you can position ROI anywhere
- **Constraints exist**: Min/max values, increment requirements (often 2 or 4 pixels)
- **Frame rate increases** significantly with smaller ROI

Example from Mako G-419:
- Full 2048×2048: ~26 fps
- ROI 2048×400: ~132 fps  
- ROI 2048×100: ~490 fps

## The Real Problem: Canvas-Based Selection Has Failed

You mentioned ROI selection on Pi has failed multiple times. The fundamental issues:

1. **Coordinate scaling**: Displayed image size ≠ actual image size
   - Browser shows image scaled to fit container
   - Canvas coordinates ≠ image pixel coordinates
   - Scaling math is error-prone across browsers

2. **Browser differences**: Pi browser vs Mac browser handle coordinates differently
   - `getBoundingClientRect()` can vary
   - Touch events vs mouse events
   - Image loading timing issues

3. **Complexity**: Canvas overlay with drag/resize is fragile
   - Many edge cases
   - Coordinate conversion at multiple points
   - Hard to debug

## What Actually Reduces Pi Load?

Ranked by effectiveness:

1. **Hardware ROI** (if Mako camera) ⭐⭐⭐⭐⭐
   - Camera only captures ROI region
   - Reduces data transfer by ~75-90% for typical ROI
   - Reduces processing load significantly
   - **BUT**: Requires setting camera's OffsetX/OffsetY/Width/Height

2. **Lower display resolution** ⭐⭐⭐⭐
   - Already implemented (1024×768 default)
   - Reduces JPEG encoding/decoding
   - Reduces network bandwidth

3. **Lower display FPS** ⭐⭐⭐
   - Already implemented (10 fps default)
   - Reduces network traffic
   - Doesn't affect capture FPS for analysis

4. **Software ROI** ⭐ (current approach)
   - Doesn't reduce capture load
   - Doesn't reduce processing load
   - Only reduces analysis area (which is already small)

## Recommendation: Simple Numeric Input Only

Given that canvas-based selection has failed multiple times, I recommend:

### Option 1: Pure Numeric Input (Simplest, Most Reliable)
- **No canvas interaction at all**
- Just 4 input fields: X, Y, Width, Height
- User types values directly
- No coordinate scaling issues
- Works identically on all browsers
- Can show preview rectangle on image (read-only, no interaction)

**Pros:**
- Zero coordinate scaling bugs
- Works everywhere
- Simple to implement
- Easy to debug
- Can validate against camera constraints

**Cons:**
- Less "intuitive" (but more reliable)
- User needs to know coordinates

### Option 2: Use Camera's Actual Frame Dimensions
- Query what the camera is actually sending
- Use those dimensions as the coordinate system
- Still use numeric inputs, but with better defaults

### Option 3: Hardware ROI for Mako (Best Performance)
- If using Mako camera, set hardware ROI directly
- Camera only captures ROI region
- Massive reduction in Pi load
- Still use numeric inputs for setting ROI

## Implementation Strategy

1. **Remove canvas-based selection entirely**
   - It has failed multiple times
   - Too complex and fragile

2. **Implement simple numeric inputs**
   - X, Y, Width, Height fields
   - Optional: Read-only preview overlay

3. **For Mako cameras: Use hardware ROI**
   - When ROI is set, call `set_roi_hardware()`
   - Camera captures only ROI region
   - Actual Pi load reduction

4. **For other cameras: Keep software cropping**
   - But acknowledge it doesn't reduce load
   - Still useful for analysis area selection

## Code Changes Needed

1. **Remove**: `roi_selector.js`, `roi_selector_sliders.js`, `roi_selector_improved.js`
2. **Add**: Simple numeric input form
3. **Update**: Mako camera to use hardware ROI when set
4. **Simplify**: No canvas coordinate conversion

## Questions to Answer

1. **Do you want hardware ROI for Mako?** (Best performance, but changes camera globally)
2. **Or keep software cropping?** (Easier, but doesn't reduce load)
3. **Numeric inputs only?** (Most reliable, less "fancy")

Let me know your preference and I'll implement the simplest solution that actually works.

