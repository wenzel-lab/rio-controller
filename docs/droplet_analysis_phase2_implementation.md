# Droplet Analysis Phase 2 Implementation
## UI Enhancements & Module Control

**Date:** December 2025

---

## Overview

Phase 2 implements UI enhancements and module control:
1. Processing rate display (Hz) in UI
2. Module enable/disable functionality

---

## Implementation Details

### 1. Processing Rate Display (FPS/Hz)

**Changes Made:**

#### `controllers/droplet_detector_controller.py`
- Added processing rate tracking variables:
  ```python
  self.processing_rate_hz = 0.0  # Current processing rate in Hz
  self.fps_frames_processed = 0  # Frames processed in current FPS window
  self.fps_window_start = time.time()  # Start time of current FPS window
  self.fps_update_interval = 1.0  # Update FPS every 1 second
  ```

- Added `_update_processing_rate()` method:
  - Calculates FPS over a 1-second sliding window
  - Updates `processing_rate_hz` every second
  - Resets counter for next window

- Modified `_processing_loop()`:
  - Calls `_update_processing_rate()` after each frame
  - Tracks frames processed in current window

- Updated `get_statistics()`:
  - Includes `processing_rate_hz` in statistics output
  - Rounded to 2 decimal places

#### `rio-webapp/controllers/droplet_web_controller.py`
- Updated `_emit_status()`:
  - Includes `processing_rate_hz` in status emission
  - Uses `getattr()` for safe access

#### `rio-webapp/static/droplet_histogram.js`
- Updated `updateStatus()`:
  - Displays processing rate: `Processing rate: X.YY Hz`
  - Shows in status alert box

#### `rio-webapp/routes.py`
- Updated `/api/droplet/status` route:
  - Includes `processing_rate_hz` in response

**How It Works:**
1. Each processed frame increments `fps_frames_processed`
2. Every 1 second, calculate: `FPS = frames_processed / elapsed_time`
3. Store in `processing_rate_hz`
4. Reset counter and start new window
5. Emit via WebSocket and display in UI

**Display Format:**
```
Status: Running | Frames: 1234 | Droplets: 5678 | Processing rate: 12.34 Hz
```

---

### 2. Module Enable/Disable

**Changes Made:**

#### `main.py`
- Added module enable check:
  ```python
  droplet_analysis_enabled = os.getenv("RIO_DROPLET_ANALYSIS_ENABLED", "true").lower() == "true"
  ```

- Conditional initialization:
  ```python
  if droplet_analysis_enabled:
      # Initialize droplet detector
  else:
      logger.info("Droplet analysis module disabled")
  ```

- Default: `true` (enabled) for backward compatibility

#### `rio-webapp/routes.py`
- Added template variable:
  ```python
  app.jinja_env.globals['droplet_analysis_enabled'] = droplet_controller is not None
  ```

#### `rio-webapp/templates/index.html`
- Conditional tab display:
  ```html
  {% if droplet_analysis_enabled %}
  <li class="nav-item">
      <button ...>Droplet Detection</button>
  </li>
  {% endif %}
  ```

- Conditional tab pane:
  ```html
  {% if droplet_analysis_enabled %}
  <div class="tab-pane fade" id="droplet-pane">
      <!-- Droplet detection UI -->
  </div>
  {% endif %}
  ```

- Conditional JavaScript initialization:
  ```javascript
  {% if droplet_analysis_enabled %}
  // Initialize droplet visualization
  {% else %}
  console.log('Droplet analysis module is disabled');
  {% endif %}
  ```

**How It Works:**
1. Check `RIO_DROPLET_ANALYSIS_ENABLED` environment variable
2. If `false`, skip droplet controller initialization
3. Pass `droplet_analysis_enabled` to template
4. Template conditionally renders UI elements
5. JavaScript only initializes if module enabled

---

## Usage

### Enable/Disable Module

**Via Environment Variable:**
```bash
# Disable module
export RIO_DROPLET_ANALYSIS_ENABLED=false
python main.py

# Enable module (default)
export RIO_DROPLET_ANALYSIS_ENABLED=true
python main.py
# Or simply:
python main.py  # Enabled by default
```

**Behavior:**
- **Enabled:** Full droplet detection UI and functionality available
- **Disabled:** 
  - No droplet controller initialized
  - No droplet tab in UI
  - No droplet detection functionality
  - Logs: "Droplet analysis module disabled"

---

## UI Changes

### Status Display

**Before:**
```
Status: Running | Frames: 1234 | Droplets: 5678
```

**After:**
```
Status: Running | Frames: 1234 | Droplets: 5678 | Processing rate: 12.34 Hz
```

### Module Disabled

**When disabled:**
- Droplet Detection tab not visible
- No droplet detection UI elements
- Console log: "Droplet analysis module is disabled"

---

## Testing

### Test Processing Rate Display

1. **Start detection:**
   - Set ROI
   - Click "Start Detection"

2. **Verify display:**
   - Status should show "Processing rate: X.YY Hz"
   - Rate should update every 1-2 seconds
   - Rate should be > 0 when processing

3. **Check accuracy:**
   - Compare displayed rate to actual frame processing
   - Should match approximately (within 0.5 Hz)

### Test Module Enable/Disable

1. **Disable module:**
   ```bash
   export RIO_DROPLET_ANALYSIS_ENABLED=false
   python main.py
   ```

2. **Verify:**
   - No droplet tab in UI
   - Log shows "Droplet analysis module disabled"
   - No errors in console

3. **Enable module:**
   ```bash
   export RIO_DROPLET_ANALYSIS_ENABLED=true
   python main.py
   ```

4. **Verify:**
   - Droplet tab visible
   - Full functionality available

---

## Files Modified

1. **`controllers/droplet_detector_controller.py`**
   - Added processing rate tracking
   - Added `_update_processing_rate()` method
   - Updated `get_statistics()` to include rate

2. **`rio-webapp/controllers/droplet_web_controller.py`**
   - Updated `_emit_status()` to include processing rate

3. **`rio-webapp/static/droplet_histogram.js`**
   - Updated `updateStatus()` to display processing rate

4. **`rio-webapp/routes.py`**
   - Added template variable for module enable state
   - Updated status route to include processing rate

5. **`rio-webapp/templates/index.html`**
   - Conditional rendering of droplet tab and pane
   - Conditional JavaScript initialization

6. **`main.py`**
   - Added module enable check
   - Conditional initialization

---

## Configuration

### Environment Variable

**Variable:** `RIO_DROPLET_ANALYSIS_ENABLED`

**Values:**
- `true` (default): Module enabled
- `false`: Module disabled

**Example:**
```bash
# In shell
export RIO_DROPLET_ANALYSIS_ENABLED=false
python main.py

# Or inline
RIO_DROPLET_ANALYSIS_ENABLED=false python main.py
```

---

## Backward Compatibility

✅ **Default behavior:** Module enabled by default  
✅ **No breaking changes:** Existing code continues to work  
✅ **Optional feature:** Can be disabled without affecting other modules  

---

## Next Steps (Phase 3)

After Phase 2 is tested and validated:

1. **Data Export** - CSV/TXT export functionality
2. **Configurable Histogram Window** - Make window size configurable
3. **REST API Endpoints** - Add POST endpoints for start/stop

---

## Status

✅ **Processing rate display:** Implemented  
✅ **Module enable/disable:** Implemented  
✅ **UI conditional rendering:** Implemented  
⏳ **Testing:** Pending  
⏳ **Documentation:** Complete  

---

**Last Updated:** December 2025
