# Droplet Analysis Phase 4 Implementation
## Configuration & API Improvements

**Date:** December 2025

---

## Overview

Phase 4 implements:
1. Configurable histogram window size
2. REST API endpoints for start/stop (already existed, verified and documented)
3. Maintained WebSocket compatibility

---

## Implementation Details

### 1. Configurable Histogram Window

**Changes Made:**

#### `droplet-detection/config.py`
- Added `histogram_window_size: int = 2000` to `DropletDetectionConfig`
- Added `histogram_bins: int = 40` to `DropletDetectionConfig`
- Added both to `to_dict()` serialization
- Added validation for both parameters (must be >= 1)

**Configuration Parameters:**
```python
# Histogram parameters
histogram_window_size: int = 2000  # Maximum number of measurements in histogram (sliding window)
histogram_bins: int = 40  # Number of bins for histogram
```

**Validation:**
- `histogram_window_size >= 1`
- `histogram_bins >= 1`

#### `controllers/droplet_detector_controller.py`
- Modified histogram initialization to use config values:
  ```python
  histogram_window_size = getattr(self.config, 'histogram_window_size', 2000)
  histogram_bins = getattr(self.config, 'histogram_bins', 40)
  self.histogram = DropletHistogram(
      maxlen=histogram_window_size, bins=histogram_bins, pixel_ratio=um_per_px, unit=unit
  )
  ```
- Added update logic in `update_config()` to recreate histogram when window size or bins change
- Note: Changing histogram parameters clears existing histogram data (by design)

**Usage:**
```python
# Set via config update
config_dict = {
    "histogram_window_size": 5000,  # Store up to 5000 measurements
    "histogram_bins": 50  # Use 50 bins for histograms
}
controller.update_config(config_dict)
```

---

### 2. REST API Endpoints

**Status:** ✅ Already implemented, verified and documented

#### `POST /api/droplet/start`

**Description:** Start droplet detection.

**Request:**
```http
POST /api/droplet/start
Content-Type: application/json
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Detection started"
}
```

**Response (Error):**
```json
{
  "success": false,
  "message": "Failed to start. Check ROI is set."
}
```
Status: 400 Bad Request

**Implementation:**
- Calls `droplet_controller.start()`
- Returns success/error based on ROI availability
- Handles exceptions gracefully

#### `POST /api/droplet/stop`

**Description:** Stop droplet detection.

**Request:**
```http
POST /api/droplet/stop
Content-Type: application/json
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Detection stopped"
}
```

**Implementation:**
- Calls `droplet_controller.stop()`
- Always succeeds (stop is idempotent)
- Handles exceptions gracefully

**Location:** `rio-webapp/routes.py` lines 138-159

---

### 3. WebSocket Compatibility

**Status:** ✅ Maintained

The REST API endpoints complement existing WebSocket commands:

**WebSocket Commands (existing):**
- `{cmd: "start"}` - Start detection
- `{cmd: "stop"}` - Stop detection
- `{cmd: "get_status"}` - Get current status

**REST API Endpoints (newly documented):**
- `POST /api/droplet/start` - Start detection
- `POST /api/droplet/stop` - Stop detection
- `GET /api/droplet/status` - Get current status

**Both methods work:**
- WebSocket: Real-time, bidirectional communication
- REST API: Standard HTTP, easier for external tools/scripts

---

## Usage Examples

### Configure Histogram Window Size

**Via Config Update:**
```python
# Update histogram window size
config_dict = {
    "histogram_window_size": 5000,  # Store 5000 measurements
    "histogram_bins": 50  # Use 50 bins
}
controller.update_config(config_dict)
```

**Via Config Profile:**
```json
{
  "histogram_window_size": 5000,
  "histogram_bins": 50,
  "min_area": 20,
  "max_area": 5000
}
```

**Via API:**
```bash
curl -X POST http://localhost:5001/api/droplet/config \
  -H "Content-Type: application/json" \
  -d '{"histogram_window_size": 5000, "histogram_bins": 50}'
```

### Start Detection via REST API

**Using curl:**
```bash
curl -X POST http://localhost:5001/api/droplet/start
```

**Using Python:**
```python
import requests
response = requests.post("http://localhost:5001/api/droplet/start")
print(response.json())
```

**Using JavaScript:**
```javascript
fetch('/api/droplet/start', { method: 'POST' })
  .then(response => response.json())
  .then(data => console.log(data));
```

### Stop Detection via REST API

**Using curl:**
```bash
curl -X POST http://localhost:5001/api/droplet/stop
```

**Using Python:**
```python
import requests
response = requests.post("http://localhost:5001/api/droplet/stop")
print(response.json())
```

---

## Configuration Parameters

### Histogram Window Size

**Parameter:** `histogram_window_size`  
**Type:** `int`  
**Default:** `2000`  
**Range:** `>= 1`  
**Description:** Maximum number of measurements to store in histogram sliding window.

**Effects:**
- Larger window: More data for statistics, higher memory usage
- Smaller window: Less memory, faster updates, less historical data

**Recommendations:**
- **Raspberry Pi:** 1000-2000 (balance memory and data retention)
- **Desktop/Server:** 5000-10000 (more data for analysis)
- **Real-time monitoring:** 500-1000 (focus on recent data)

### Histogram Bins

**Parameter:** `histogram_bins`  
**Type:** `int`  
**Default:** `40`  
**Range:** `>= 1`  
**Description:** Number of bins for histogram visualization.

**Effects:**
- More bins: Finer resolution, more detailed histograms
- Fewer bins: Coarser resolution, smoother histograms

**Recommendations:**
- **Standard:** 40 bins (good balance)
- **High resolution:** 50-100 bins (detailed analysis)
- **Low resolution:** 20-30 bins (smoother visualization)

---

## Testing

### Test Histogram Window Size

1. **Set small window:**
   ```python
   config_dict = {"histogram_window_size": 100}
   controller.update_config(config_dict)
   ```

2. **Process many frames:**
   - Start detection
   - Process > 100 droplets
   - Verify histogram contains only most recent 100

3. **Set large window:**
   ```python
   config_dict = {"histogram_window_size": 5000}
   controller.update_config(config_dict)
   ```

4. **Verify histogram resized:**
   - Check histogram can store up to 5000 measurements
   - Verify statistics update correctly

### Test REST API Endpoints

**Start Endpoint:**
```bash
# Test start
curl -X POST http://localhost:5001/api/droplet/start

# Expected: {"success": true, "message": "Detection started"}
```

**Stop Endpoint:**
```bash
# Test stop
curl -X POST http://localhost:5001/api/droplet/stop

# Expected: {"success": true, "message": "Detection stopped"}
```

**Error Handling:**
```bash
# Test without ROI (should fail)
# (Set ROI first, then unset it, then try start)
curl -X POST http://localhost:5001/api/droplet/start

# Expected: {"success": false, "message": "Failed to start. Check ROI is set."}
```

---

## Memory Considerations

### Histogram Window Size Impact

**Memory per measurement:** ~100 bytes  
**Total memory for window:**
- 1000 measurements: ~100 KB
- 2000 measurements: ~200 KB (default)
- 5000 measurements: ~500 KB
- 10000 measurements: ~1 MB

**Recommendations:**
- **Raspberry Pi (512 MB RAM):** 1000-2000
- **Raspberry Pi (1 GB+ RAM):** 2000-5000
- **Desktop/Server:** 5000-10000

---

## Files Modified

1. **`droplet-detection/config.py`**
   - Added `histogram_window_size` and `histogram_bins` parameters
   - Added to `to_dict()` serialization
   - Added validation

2. **`controllers/droplet_detector_controller.py`**
   - Modified histogram initialization to use config values
   - Added update logic for histogram parameters

3. **`rio-webapp/routes.py`**
   - Verified existing REST API endpoints (no changes needed)
   - Endpoints already properly implemented

---

## API Documentation Summary

### REST API Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/api/droplet/start` | POST | Start detection | `{success: bool, message: string}` |
| `/api/droplet/stop` | POST | Stop detection | `{success: bool, message: string}` |
| `/api/droplet/status` | GET | Get status | `{running, frame_count, ...}` |
| `/api/droplet/config` | POST | Update config | `{success: bool}` |
| `/api/droplet/export` | GET | Export data | File download |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `droplet` | Client→Server | Send command: `{cmd: "start"\|"stop"\|"get_status"}` |
| `droplet:status` | Server→Client | Status update |
| `droplet:histogram` | Server→Client | Histogram data |
| `droplet:statistics` | Server→Client | Statistics data |

---

## Backward Compatibility

### Default Values

- **histogram_window_size:** Defaults to 2000 (unchanged behavior)
- **histogram_bins:** Defaults to 40 (unchanged behavior)

### Existing Code

- All existing code continues to work
- No breaking changes
- Config files without new parameters use defaults

---

## Status

✅ **Configurable histogram window:** Implemented  
✅ **REST API endpoints:** Verified and documented  
✅ **WebSocket compatibility:** Maintained  
⏳ **Testing:** Pending  

---

**Last Updated:** December 2025
