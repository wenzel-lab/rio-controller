# Pi Load Optimization - Implementation Clarification

**Date:** 2024  
**Purpose:** Clarify what frame skipping is implemented vs removed

---

## Key Distinction

There are **TWO SEPARATE** frame rate controls:

1. **Display Frame Rate Limiting** (for web streaming) - ✅ **KEPT & WORKING**
2. **Analysis Frame Skipping** (for droplet detection) - ❌ **REMOVED** (correctly)

---

## ✅ 1. Display Frame Rate Limiting (KEPT)

**Purpose:** Reduce Pi load when streaming video to web clients  
**Location:** `software/rio-webapp/routes.py` - `/video` route  
**Status:** ✅ **IMPLEMENTED AND WORKING**

### How It Works

```python
# In routes.py - /video route
CAMERA_DISPLAY_FPS = 10  # Default: 10 fps for web streaming

def generate_frames():
    """Generator for MJPEG frames with frame rate limiting."""
    last_frame_time = 0.0
    frame_interval = 1.0 / float(display_fps)  # 0.1 seconds for 10 fps
    
    while True:
        current_time = time.time()
        # Only yield frame if enough time has passed (frame rate limiting)
        if current_time - last_frame_time >= frame_interval:
            frame = cam.get_frame()
            if frame:
                yield frame
            last_frame_time = current_time
        else:
            time.sleep(0.01)  # Small sleep to avoid busy waiting
```

### What This Does

- **Camera captures at:** 30 fps (CAMERA_THREAD_FPS)
- **Web clients receive:** 10 fps (CAMERA_DISPLAY_FPS)
- **Result:** Reduces network bandwidth and Pi CPU for web streaming
- **Analysis:** Still gets all frames (see below)

### Configuration

```python
# In config.py
CAMERA_DISPLAY_FPS = 10  # Display frame rate (for web streaming, lower to reduce Pi load)
```

**This is IMPORTANT and should be KEPT** - it reduces Pi load for web streaming without affecting analysis.

---

## ❌ 2. Analysis Frame Skipping (REMOVED)

**Purpose:** Would have reduced CPU by skipping frames in droplet detection  
**Location:** `software/controllers/camera.py` - `_feed_frame_to_droplet_detector()`  
**Status:** ❌ **REMOVED** (correctly - we need all frames for analysis)

### What Was Removed

**Previously (WRONG - removed):**
```python
# Frame skipping: process every Nth frame to reduce CPU load
self._droplet_frame_counter += 1
if self._droplet_frame_counter % DROPLET_DETECTION_FRAME_SKIP != 0:
    return  # Skip this frame
```

**Now (CORRECT):**
```python
# All frames are processed when running (no frame skipping - we need the data)
if roi_frame is not None:
    # Add frame to droplet detector processing queue
    self.droplet_controller.add_frame(roi_frame)  # ALL frames fed
```

### What This Means

- **Camera captures at:** 30 fps
- **Analysis processes:** ALL 30 fps (no skipping)
- **Result:** Complete data collection for accurate analysis
- **Display:** Still limited to 10 fps for web clients (separate control)

### Why This Was Removed

- **Data integrity:** We need all frames for accurate droplet detection
- **Analysis quality:** Skipping frames could miss droplets or reduce accuracy
- **User requirement:** "we need that data" - all frames must be analyzed

---

## Current Implementation Summary

### ✅ Display (Web Streaming)
- **Frame Rate:** Limited to 10 fps (CAMERA_DISPLAY_FPS)
- **Location:** `routes.py` - `/video` route
- **Purpose:** Reduce Pi load for web streaming
- **Status:** ✅ **WORKING**

### ✅ Analysis (Droplet Detection)
- **Frame Rate:** All frames (30 fps, no skipping)
- **Location:** `camera.py` - `_feed_frame_to_droplet_detector()`
- **Purpose:** Complete data collection for accurate analysis
- **Status:** ✅ **WORKING** (all frames processed)

### ✅ Camera Capture
- **Frame Rate:** 30 fps (CAMERA_THREAD_FPS)
- **Location:** Camera thread in `camera.py`
- **Purpose:** Full frame rate capture
- **Status:** ✅ **WORKING**

---

## Data Flow

```
Camera Hardware
    ↓ (30 fps capture)
Camera Thread (camera.py)
    ↓ (30 fps - all frames)
    ├─→ Web Streaming (routes.py)
    │   └─→ Limited to 10 fps (CAMERA_DISPLAY_FPS) ✅
    │
    └─→ Droplet Detection (camera.py)
        └─→ ALL 30 fps processed (no skipping) ✅
```

---

## Configuration Values

### Display Frame Rate
```python
# config.py
CAMERA_DISPLAY_FPS = 10  # Frames per second sent to web clients
```

### Camera Capture Rate
```python
# config.py
CAMERA_THREAD_FPS = 30  # Frames per second captured by camera
```

### Analysis Frame Rate
- **No configuration needed** - processes ALL frames from camera (30 fps)
- **No skipping** - all frames are analyzed

---

## What Was Changed

### ✅ Kept
1. **Display FPS limiting** - Still limits web streaming to 10 fps
2. **Conditional processing** - Only feeds frames when detection running
3. **JPEG quality optimization** - Streaming vs snapshot quality

### ❌ Removed
1. **Analysis frame skipping** - Removed frame skip counter and logic
2. **DROPLET_DETECTION_FRAME_SKIP config** - Removed from config.py

### ✅ Added
1. **Logging optimization** - Configurable log level
2. **Lazy camera initialization** - Starts only when client connects

---

## Verification

### Display Frame Rate Limiting
- ✅ Check `routes.py` line 350-365 - frame interval limiting is present
- ✅ Check `config.py` line 17 - CAMERA_DISPLAY_FPS = 10
- ✅ This limits frames sent to web clients to 10 fps

### Analysis Frame Processing
- ✅ Check `camera.py` line 604-641 - `_feed_frame_to_droplet_detector()`
- ✅ No frame skipping logic present
- ✅ All frames are fed when detection is running

---

## Summary

| Component | Frame Rate | Skipping? | Status |
|-----------|------------|-----------|--------|
| **Camera Capture** | 30 fps | No | ✅ Working |
| **Web Display** | 10 fps | Yes (limited) | ✅ Working |
| **Analysis** | 30 fps | No (all frames) | ✅ Working |

**Key Points:**
- ✅ Display frame limiting: **KEPT** (reduces Pi load for web streaming)
- ❌ Analysis frame skipping: **REMOVED** (we need all frames for data)
- ✅ Both work independently (display limited, analysis gets all frames)

---

**Clarification Complete** ✅

