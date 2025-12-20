# Raspberry Pi Load Optimization Recommendations

**Document Version:** 1.0  
**Date:** 2024  
**Purpose:** Comprehensive analysis and recommendations for reducing CPU, memory, and network load on Raspberry Pi systems running the microfluidics workstation software.

---

## Executive Summary

This document provides 12 prioritized recommendations to reduce system load on Raspberry Pi devices, with expected cumulative improvements of **40-60% CPU reduction**, **30-50% memory reduction**, and **50-70% network bandwidth reduction**. The recommendations are organized by implementation priority and expected impact.

**Key Findings:**
- Current system processes every frame at full resolution for both display and analysis
- Excessive logging and WebSocket updates create unnecessary overhead
- No frame skipping or adaptive quality mechanisms
- Hardware encoding capabilities underutilized
- Memory management could be improved

**Quick Wins (High Impact, Low Effort):**
1. JPEG quality reduction for streaming (30-50% bandwidth reduction)
2. Droplet detection frame skipping (50-66% CPU reduction)
3. Conditional droplet processing (eliminates idle overhead)
4. Logging level optimization (10-15% CPU reduction)

---

## 1. Current State Analysis

### 1.1 Performance Bottlenecks Identified

#### Image Processing Pipeline
- **Current:** All frames encoded at JPEG quality 95 (Mako) or default quality
- **Issue:** High quality unnecessary for streaming, wastes CPU and bandwidth
- **Location:** `software/drivers/camera/mako_camera.py:131`, `pi_camera_v2.py:127`

#### Frame Processing
- **Current:** Every frame from camera thread (30 fps) fed to droplet detector
- **Issue:** Droplet analysis doesn't need 30 fps; 10-15 fps sufficient
- **Location:** `software/controllers/camera.py:639` (`_feed_frame_to_droplet_detector`)

#### Logging Overhead
- **Current:** 98+ logger calls in `camera.py` alone, many at INFO/DEBUG level
- **Issue:** String formatting and I/O operations consume CPU
- **Location:** Throughout `software/controllers/camera.py`

#### WebSocket Updates
- **Current:** 5+ events emitted every 1 second to all clients, regardless of changes
- **Issue:** Unnecessary network traffic and CPU for formatting
- **Location:** `software/rio-webapp/routes.py:396-419`

#### Hardware Polling
- **Current:** Heaters and flow controllers polled every 1 second
- **Issue:** Polling continues even when not actively controlled
- **Location:** `software/rio-webapp/routes.py:402-405`

#### Memory Management
- **Current:** No explicit queue size limits, frames accumulate in memory
- **Issue:** Potential memory buildup during high frame rates
- **Location:** `software/controllers/droplet_detector_controller.py:529`

### 1.2 Current Configuration Values

```python
# From software/config.py
CAMERA_DISPLAY_FPS = 10  # Display frame rate (good)
CAMERA_THREAD_FPS = 30   # Capture frame rate (may be excessive)
BACKGROUND_UPDATE_INTERVAL_S = 1.0  # WebSocket update interval
```

### 1.3 Resource Usage Estimates

Based on code analysis:
- **CPU:** ~60-80% during active droplet detection (30 fps processing)
- **Memory:** ~200-400 MB for frame queues and buffers
- **Network:** ~5-10 Mbps for video streaming at 1024x768, quality 95
- **I/O:** High logging overhead (estimated 10-15% CPU)

---

## 2. Detailed Recommendations

### 2.1 JPEG Quality/Compression Optimization ⭐ **HIGH PRIORITY**

**Impact:** 🔥🔥🔥 **Very High** (30-50% bandwidth, 20-30% encoding CPU)  
**Effort:** ⚡ **Low** (1-2 hours)  
**Risk:** ⚠️ **Low** (easily reversible)

#### Current State
- Mako camera: Default JPEG quality (likely 95)
- Pi cameras: Quality 95 for snapshots, no explicit quality for streaming
- No quality differentiation between streaming and snapshots

#### Recommendation
Add configurable JPEG quality with different defaults for streaming vs. snapshots:

```python
# Add to software/config.py
CAMERA_STREAMING_JPEG_QUALITY = 75  # For web streaming (lower quality)
CAMERA_SNAPSHOT_JPEG_QUALITY = 95   # For snapshots (high quality)
```

#### Implementation Details
1. **Mako Camera** (`software/drivers/camera/mako_camera.py:131`):
   ```python
   _, buffer = cv2.imencode(
       ".jpg", opencv_image,
       [cv2.IMWRITE_JPEG_QUALITY, CAMERA_STREAMING_JPEG_QUALITY]
   )
   ```

2. **Pi Camera V2** (`software/drivers/camera/pi_camera_v2.py:127`):
   ```python
   ret, buffer = cv2.imencode(
       ".jpg", frame,
       [cv2.IMWRITE_JPEG_QUALITY, CAMERA_STREAMING_JPEG_QUALITY]
   )
   ```

3. **Pi Camera Legacy** (`software/drivers/camera/pi_camera_legacy.py`):
   - Already uses hardware encoding, but can adjust quality parameter

4. **Snapshots** (`software/controllers/camera.py:552`):
   - Keep quality 95 for snapshots (user expects high quality)

#### Expected Benefits
- **Bandwidth:** 30-50% reduction (quality 95 → 75 typically reduces file size by 40-50%)
- **CPU:** 20-30% reduction in JPEG encoding time
- **Network Latency:** Lower latency due to smaller packets

#### Testing Considerations
- Visual quality assessment at different quality levels
- Measure actual file size reduction
- Verify no artifacts in droplet detection (lower quality shouldn't affect analysis)

---

### 2.2 Droplet Detection Frame Skipping ⭐ **HIGH PRIORITY**

**Impact:** 🔥🔥🔥 **Very High** (50-66% CPU reduction in droplet processing)  
**Effort:** ⚡ **Low** (2-3 hours)  
**Risk:** ⚠️ **Low** (configurable, can disable)

#### Current State
- Every frame from camera (30 fps) is processed by droplet detector
- No frame skipping mechanism
- Processing queue can fill up during high activity

#### Recommendation
Implement configurable frame skipping for droplet detection:

```python
# Add to software/config.py
DROPLET_DETECTION_FRAME_SKIP = 2  # Process every Nth frame (1 = all, 2 = every other, etc.)
```

#### Implementation Details
1. **Camera Controller** (`software/controllers/camera.py:559-592`):
   ```python
   def _feed_frame_to_droplet_detector(self) -> None:
       """Feed frame to droplet detector with frame skipping."""
       if not self.droplet_controller or not self.roi:
           return
       
       # Frame skipping counter
       if not hasattr(self, '_droplet_frame_counter'):
           self._droplet_frame_counter = 0
       
       self._droplet_frame_counter += 1
       skip_rate = DROPLET_DETECTION_FRAME_SKIP
       
       # Only process every Nth frame
       if self._droplet_frame_counter % skip_rate != 0:
           return
       
       # ... existing frame feeding logic ...
   ```

2. **Configuration** (`software/droplet-detection/config.py`):
   - Add `frame_skip` parameter to `DropletDetectionConfig`
   - Default: 2 (process every other frame = 15 fps from 30 fps source)

#### Expected Benefits
- **CPU:** 50% reduction with skip=2, 66% with skip=3
- **Memory:** Reduced queue pressure
- **Latency:** Lower processing latency (queue empties faster)

#### Scientific Validity
- **10-15 fps sufficient** for droplet detection (droplets move slowly)
- Frame skipping is common in computer vision pipelines
- Can be adjusted per experiment requirements

#### Testing Considerations
- Verify droplet detection accuracy at different skip rates
- Measure actual CPU usage reduction
- Test with high droplet density scenarios

---

### 2.3 Conditional Droplet Processing ⭐ **HIGH PRIORITY**

**Impact:** 🔥🔥 **High** (Eliminates idle overhead)  
**Effort:** ⚡ **Very Low** (30 minutes)  
**Risk:** ⚠️ **Very Low** (simple boolean check)

#### Current State
- Frames fed to droplet detector whenever ROI is set, even if detection is stopped
- No check if droplet detection is actively running

#### Recommendation
Only feed frames when droplet detection is actively running:

```python
# In software/controllers/camera.py:_feed_frame_to_droplet_detector
def _feed_frame_to_droplet_detector(self) -> None:
    """Feed frame to droplet detector if running."""
    if not self.droplet_controller:
        return
    
    # Check if detection is actually running
    if not hasattr(self.droplet_controller, 'running') or not self.droplet_controller.running:
        return
    
    # ... existing logic ...
```

#### Expected Benefits
- **CPU:** Eliminates unnecessary queue operations when detection stopped
- **Memory:** Prevents queue buildup when not needed
- **Cleaner State:** Clear separation between ROI selection and active detection

---

### 2.4 Logging Level Optimization ⭐ **MEDIUM PRIORITY**

**Impact:** 🔥🔥 **High** (10-15% CPU reduction)  
**Effort:** ⚡ **Low** (2-3 hours)  
**Risk:** ⚠️ **Low** (can adjust per environment)

#### Current State
- Logging level: `INFO` (set in `software/main.py:77`)
- 98+ logger calls in `camera.py` alone
- Many verbose logs at INFO/DEBUG level
- Frame-by-frame logging in some paths

#### Recommendation
1. **Production Logging Level:**
   ```python
   # In software/main.py
   log_level = os.getenv("RIO_LOG_LEVEL", "WARNING").upper()
   logging.basicConfig(level=getattr(logging, log_level), ...)
   ```

2. **Conditional Verbose Logging:**
   ```python
   # Log every Nth frame instead of every frame
   if frame_count % 100 == 0:
       logger.debug(f"Frame {frame_count} processed")
   ```

3. **Remove Redundant Logs:**
   - Remove "First frame received!" type logs after initial setup
   - Reduce periodic stats logging frequency

#### Expected Benefits
- **CPU:** 10-15% reduction (string formatting and I/O are expensive)
- **Disk I/O:** Reduced log file growth
- **Debugging:** Still available via environment variable

#### Implementation Strategy
- Use `RIO_LOG_LEVEL=INFO` for development
- Use `RIO_LOG_LEVEL=WARNING` for production
- Keep ERROR logs always enabled

---

### 2.5 WebSocket Update Throttling ⭐ **MEDIUM PRIORITY**

**Impact:** 🔥🔥 **High** (20-30% network/CPU reduction)  
**Effort:** ⚡⚡ **Medium** (4-6 hours)  
**Risk:** ⚠️ **Medium** (requires careful state tracking)

#### Current State
- Background loop emits 5+ events every 1 second
- Updates sent even when values haven't changed
- All clients receive all updates regardless of interest

#### Recommendation
1. **Change-Based Updates:**
   ```python
   # Track previous values, only emit on change
   class BackgroundUpdater:
       def __init__(self):
           self.last_heater_data = None
           self.last_flow_data = None
           # ...
       
       def should_emit(self, new_data, last_data, threshold=0.1):
           """Emit only if change exceeds threshold."""
           if last_data is None:
               return True
           # Compare and return True only if significant change
   ```

2. **Adaptive Update Intervals:**
   ```python
   # Faster updates when actively controlled, slower when idle
   if any_heater_active or flow_active:
       update_interval = 0.5  # 2 Hz
   else:
       update_interval = 3.0  # 0.33 Hz
   ```

3. **Client-Specific Updates:**
   - Only emit to clients that have subscribed to specific events
   - Implement WebSocket rooms/channels

#### Expected Benefits
- **Network:** 50-70% reduction in WebSocket traffic
- **CPU:** 20-30% reduction in data formatting
- **Responsiveness:** Still fast when actively controlling

---

### 2.6 Hardware Polling Frequency Reduction ⭐ **MEDIUM PRIORITY**

**Impact:** 🔥 **Medium** (10-15% SPI/CPU reduction)  
**Effort:** ⚡ **Low** (2-3 hours)  
**Risk:** ⚠️ **Low** (configurable intervals)

#### Current State
- Heaters and flow controllers polled every 1 second
- Polling continues even when not actively controlled

#### Recommendation
Implement adaptive polling based on activity:

```python
# In software/rio-webapp/routes.py:background_update_loop
def background_update_loop():
    base_interval = 1.0
    idle_interval = 3.0
    
    while True:
        # Check if any device is actively being controlled
        active_control = (
            any(h.is_active() for h in heaters) or
            flow.is_active()
        )
        
        interval = base_interval if active_control else idle_interval
        
        time.sleep(interval)
        
        # Update hardware
        cam.update_strobe_data()
        for heater in heaters:
            heater.update()
        flow.update()
        # ...
```

#### Expected Benefits
- **SPI Communication:** 66% reduction when idle (1s → 3s)
- **CPU:** 10-15% reduction in hardware communication overhead
- **Responsiveness:** Still fast when actively controlling

---

### 2.7 Lower Default Display Resolution ⭐ **MEDIUM PRIORITY**

**Impact:** 🔥🔥 **High** (4x pixel reduction at 640x480)  
**Effort:** ⚡ **Very Low** (30 minutes)  
**Risk:** ⚠️ **Very Low** (user can still change)

#### Current State
- Default display resolution: 1024x768 (`CAMERA_THREAD_WIDTH/HEIGHT`)
- Higher resolutions available but may be overkill for streaming

#### Recommendation
Change default to 640x480 for display/streaming:

```python
# In software/config.py
CAMERA_THREAD_WIDTH = 640   # Changed from 1024
CAMERA_THREAD_HEIGHT = 480   # Changed from 768
```

Keep higher resolutions available for snapshots.

#### Expected Benefits
- **CPU:** 4x reduction in pixel processing (1024x768 = 786K pixels vs 640x480 = 307K pixels)
- **Memory:** 4x reduction in frame buffer size
- **Network:** 4x reduction in bandwidth (with same JPEG quality)

#### User Impact
- Users can still select higher resolutions if needed
- Snapshots can use full sensor resolution
- Display quality still acceptable for monitoring

---

### 2.8 Memory Management Improvements ⭐ **LOW PRIORITY**

**Impact:** 🔥 **Medium** (Prevents memory buildup)  
**Effort:** ⚡⚡ **Medium** (3-4 hours)  
**Risk:** ⚠️ **Low** (defensive programming)

#### Current State
- Frame queues have no explicit size limits
- Old frames can accumulate in memory
- No explicit cleanup of processed frames

#### Recommendation
1. **Queue Size Limits:**
   ```python
   # In software/controllers/droplet_detector_controller.py
   self.frame_queue = queue.Queue(maxsize=10)  # Limit to 10 frames
   ```

2. **Explicit Buffer Cleanup:**
   ```python
   # After processing, explicitly clear references
   frame = None
   del frame
   ```

3. **Memory-Mapped Buffers:**
   - Use shared memory for large frame buffers where possible

#### Expected Benefits
- **Memory:** Prevents unbounded growth
- **Stability:** Reduces risk of OOM errors
- **Performance:** Lower memory pressure = better cache performance

---

### 2.9 Image Encoding Pipeline Optimization ⭐ **LOW PRIORITY**

**Impact:** 🔥 **Medium** (10-15% encoding CPU reduction)  
**Effort:** ⚡⚡⚡ **High** (6-8 hours)  
**Risk:** ⚠️ **Medium** (requires hardware-specific testing)

#### Current State
- Multiple color space conversions (BGR→RGB)
- Software JPEG encoding for all cameras
- No use of hardware encoding on Pi cameras

#### Recommendation
1. **Use Hardware Encoding (Pi Cameras):**
   - `picamera2` supports hardware JPEG encoding
   - Avoid unnecessary color conversions

2. **Cache Encoding Parameters:**
   ```python
   # Cache JPEG encoding parameters
   self._jpeg_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
   ```

3. **Optimize Color Conversions:**
   - Only convert when necessary
   - Use in-place operations where possible

#### Expected Benefits
- **CPU:** 10-15% reduction in encoding time (hardware acceleration)
- **Latency:** Lower encoding latency

#### Implementation Complexity
- Requires testing on actual hardware
- May need fallback to software encoding

---

### 2.10 Network Format Optimization ⭐ **LOW PRIORITY**

**Impact:** 🔥 **Medium** (Better compression than JPEG)  
**Effort:** ⚡⚡⚡ **High** (8-10 hours)  
**Risk:** ⚠️ **Medium** (browser compatibility)

#### Current State
- JPEG encoding for all streaming
- No alternative formats considered

#### Recommendation
Consider WebP format for better compression:

```python
# WebP typically 25-35% smaller than JPEG at same quality
_, buffer = cv2.imencode(".webp", frame, [cv2.IMWRITE_WEBP_QUALITY, 75])
```

#### Expected Benefits
- **Bandwidth:** 25-35% additional reduction vs. JPEG
- **Quality:** Better quality at same file size

#### Considerations
- Browser support (Chrome, Firefox, Edge support WebP)
- Fallback to JPEG for older browsers
- May require additional OpenCV build options

---

### 2.11 Adaptive Frame Rate Limiting ⭐ **LOW PRIORITY**

**Impact:** 🔥 **Medium** (Prevents overload)  
**Effort:** ⚡⚡ **Medium** (4-5 hours)  
**Risk:** ⚠️ **Low** (defensive mechanism)

#### Current State
- Fixed 10 fps display limit
- No adaptation based on system load

#### Recommendation
Implement CPU-load-based FPS adjustment:

```python
import psutil

def get_cpu_load():
    return psutil.cpu_percent(interval=0.1)

def adaptive_fps():
    cpu_load = get_cpu_load()
    if cpu_load > 80:
        return 5  # Reduce to 5 fps
    elif cpu_load > 60:
        return 7  # Reduce to 7 fps
    else:
        return 10  # Normal 10 fps
```

#### Expected Benefits
- **Stability:** Prevents system overload
- **Responsiveness:** Automatically adjusts to conditions

#### Considerations
- Requires `psutil` dependency
- May cause visual stuttering if too aggressive

---

### 2.12 Lazy Initialization ⭐ **LOW PRIORITY**

**Impact:** 🔥 **Low** (Reduces startup overhead)  
**Effort:** ⚡⚡ **Medium** (3-4 hours)  
**Risk:** ⚠️ **Low** (defensive programming)

#### Current State
- Some components initialized even when not used
- Camera starts immediately

#### Recommendation
1. **Lazy Droplet Detector:**
   - Initialize only when ROI is set and detection started

2. **Delayed Camera Start:**
   - Start camera only when first client connects to `/video`

3. **Lazy Module Loading:**
   - Import heavy modules only when needed

#### Expected Benefits
- **Startup Time:** Faster application startup
- **Idle CPU:** Lower CPU when not actively used

---

## 3. Implementation Roadmap

### Phase 1: Quick Wins (Week 1)
**Target:** 40-50% CPU reduction, 30-40% bandwidth reduction

1. ✅ JPEG quality optimization (#2.1) - **2 hours**
2. ✅ Droplet detection frame skipping (#2.2) - **3 hours**
3. ✅ Conditional droplet processing (#2.3) - **30 minutes**
4. ✅ Logging level optimization (#2.4) - **2 hours**

**Total Effort:** ~8 hours  
**Expected Impact:** High

### Phase 2: Medium Effort (Week 2)
**Target:** Additional 20-30% improvements

5. WebSocket update throttling (#2.5) - **5 hours**
6. Hardware polling frequency (#2.6) - **3 hours**
7. Lower default resolution (#2.7) - **30 minutes**

**Total Effort:** ~9 hours  
**Expected Impact:** Medium-High

### Phase 3: Polish (Week 3-4)
**Target:** Stability and edge cases

8. Memory management (#2.8) - **4 hours**
9. Encoding optimization (#2.9) - **7 hours** (if hardware available)
10. Adaptive FPS (#2.11) - **5 hours**
11. Lazy initialization (#2.12) - **4 hours**

**Total Effort:** ~20 hours  
**Expected Impact:** Medium

### Phase 4: Advanced (Optional)
12. Network format optimization (#2.10) - **9 hours**

---

## 4. Expected Performance Gains

### Cumulative Impact Estimates

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| **CPU Usage** | 60-80% | 35-50% | 25-40% | 20-35% |
| **Memory Usage** | 200-400 MB | 150-300 MB | 120-250 MB | 100-200 MB |
| **Network Bandwidth** | 5-10 Mbps | 2.5-5 Mbps | 1.5-3 Mbps | 1-2.5 Mbps |
| **Frame Processing** | 30 fps | 15 fps | 15 fps | 10-15 fps |
| **WebSocket Updates** | 5/sec | 5/sec | 1-2/sec | 0.5-1/sec |

### Individual Contribution Estimates

| Recommendation | CPU Reduction | Memory Reduction | Bandwidth Reduction |
|----------------|---------------|------------------|---------------------|
| JPEG Quality | 20-30% | - | 30-50% |
| Frame Skipping | 50-66% (droplet) | 20-30% | - |
| Conditional Processing | 5-10% (idle) | 10-20% | - |
| Logging Optimization | 10-15% | - | - |
| WebSocket Throttling | 20-30% | - | 50-70% |
| Polling Frequency | 10-15% | - | - |
| Lower Resolution | 30-40% | 30-40% | 30-40% |
| Memory Management | - | 20-30% | - |

---

## 5. Risk Assessment

### Low Risk (Safe to Implement)
- ✅ JPEG quality reduction (#2.1)
- ✅ Frame skipping (#2.2)
- ✅ Conditional processing (#2.3)
- ✅ Logging optimization (#2.4)
- ✅ Lower default resolution (#2.7)
- ✅ Memory management (#2.8)

### Medium Risk (Requires Testing)
- ⚠️ WebSocket throttling (#2.5) - May affect UI responsiveness
- ⚠️ Hardware polling (#2.6) - May miss rapid changes
- ⚠️ Encoding optimization (#2.9) - Hardware-specific
- ⚠️ Adaptive FPS (#2.11) - May cause visual stuttering

### Higher Risk (Requires Careful Implementation)
- 🔴 Network format (#2.10) - Browser compatibility
- 🔴 Lazy initialization (#2.12) - May break existing workflows

---

## 6. Testing Strategy

### Performance Testing
1. **Baseline Measurements:**
   - CPU usage during idle and active states
   - Memory usage over 1-hour period
   - Network bandwidth during streaming
   - Frame processing latency

2. **After Each Phase:**
   - Repeat baseline measurements
   - Compare against previous phase
   - Verify no regressions in functionality

3. **Stress Testing:**
   - High droplet density scenarios
   - Multiple simultaneous clients
   - Extended operation (24+ hours)

### Functional Testing
1. **Droplet Detection Accuracy:**
   - Verify detection quality at different frame skip rates
   - Test with various droplet sizes and densities

2. **UI Responsiveness:**
   - Verify WebSocket updates still timely
   - Test hardware control responsiveness

3. **Visual Quality:**
   - Assess JPEG quality at different settings
   - Verify acceptable quality for monitoring

---

## 7. Configuration Options

### Recommended Configuration File Additions

```python
# software/config.py additions

# Image Quality
CAMERA_STREAMING_JPEG_QUALITY = 75  # For web streaming
CAMERA_SNAPSHOT_JPEG_QUALITY = 95   # For snapshots

# Droplet Detection
DROPLET_DETECTION_FRAME_SKIP = 2    # Process every Nth frame
DROPLET_DETECTION_MAX_QUEUE_SIZE = 10  # Max frames in queue

# WebSocket Updates
WEBSOCKET_UPDATE_INTERVAL_ACTIVE = 0.5   # When actively controlling (seconds)
WEBSOCKET_UPDATE_INTERVAL_IDLE = 3.0    # When idle (seconds)
WEBSOCKET_CHANGE_THRESHOLD = 0.1         # Minimum change to emit update

# Hardware Polling
HARDWARE_POLL_INTERVAL_ACTIVE = 1.0      # When actively controlling (seconds)
HARDWARE_POLL_INTERVAL_IDLE = 3.0        # When idle (seconds)

# Adaptive FPS
ADAPTIVE_FPS_ENABLED = True
ADAPTIVE_FPS_CPU_THRESHOLD_HIGH = 80     # Reduce FPS if CPU > this %
ADAPTIVE_FPS_CPU_THRESHOLD_MEDIUM = 60   # Moderate FPS if CPU > this %

# Logging
RIO_LOG_LEVEL = "WARNING"  # Production default (INFO for development)
```

### Environment Variables

```bash
# Production settings
export RIO_LOG_LEVEL=WARNING
export RIO_DROPLET_FRAME_SKIP=2
export RIO_JPEG_QUALITY_STREAMING=75

# Development settings
export RIO_LOG_LEVEL=INFO
export RIO_DROPLET_FRAME_SKIP=1
export RIO_JPEG_QUALITY_STREAMING=85
```

---

## 8. Monitoring and Validation

### Key Metrics to Track

1. **CPU Usage:**
   ```bash
   top -p $(pgrep -f "python.*main.py")
   ```

2. **Memory Usage:**
   ```bash
   ps aux | grep "python.*main.py" | awk '{print $6/1024 " MB"}'
   ```

3. **Network Bandwidth:**
   ```bash
   iftop -i eth0  # or wlan0
   ```

4. **Frame Processing Rate:**
   - Check logs for "Processing rate: X fps"
   - Monitor droplet detector statistics

### Validation Checklist

- [ ] CPU usage reduced by 40-50% during active operation
- [ ] Memory usage stable (no continuous growth)
- [ ] Network bandwidth reduced by 30-50%
- [ ] Droplet detection accuracy maintained
- [ ] UI remains responsive
- [ ] No visual quality degradation (acceptable for monitoring)
- [ ] System stable over 24-hour period
- [ ] All existing functionality works

---

## 9. Conclusion

The recommendations in this document provide a comprehensive approach to reducing Raspberry Pi load, with **Phase 1 (Quick Wins) alone expected to reduce CPU by 40-50% and bandwidth by 30-40%**. The phased implementation approach allows for incremental improvements with low risk.

**Priority Actions:**
1. Implement Phase 1 recommendations immediately (high impact, low risk)
2. Test and validate performance improvements
3. Proceed to Phase 2 based on results
4. Consider Phase 3/4 for additional polish

**Expected Timeline:**
- **Week 1:** Phase 1 implementation and testing
- **Week 2:** Phase 2 implementation and validation
- **Week 3-4:** Phase 3 polish and edge cases
- **Ongoing:** Monitor and adjust based on real-world usage

---

## Appendix A: Code Locations Reference

| Component | File Path | Key Lines |
|-----------|-----------|-----------|
| Camera Controller | `software/controllers/camera.py` | 559-592 (droplet feeding), 631 (frame loop) |
| Mako Camera | `software/drivers/camera/mako_camera.py` | 131 (JPEG encoding) |
| Pi Camera V2 | `software/drivers/camera/pi_camera_v2.py` | 127 (JPEG encoding) |
| Background Updates | `software/rio-webapp/routes.py` | 396-419 (update loop) |
| Droplet Controller | `software/controllers/droplet_detector_controller.py` | 504-533 (frame queue) |
| Config | `software/config.py` | All constants |
| Main Entry | `software/main.py` | 76-78 (logging config) |

---

## Appendix B: Related Documentation

- `docs/roi-implementation-summary.md` - ROI hardware implementation
- `docs/pi-camera-hardware-roi-support.md` - Pi camera ROI details
- `docs/roi-analysis-and-recommendations.md` - ROI analysis

---

**Document End**

