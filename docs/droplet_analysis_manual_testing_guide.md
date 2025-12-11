# Droplet Analysis Manual Testing Guide
## Step-by-Step Testing Instructions

**Date:** December 2025

---

## Pre-Testing Setup

### 1. Environment Setup

**On Raspberry Pi (32-bit or 64-bit):**
```bash
# Activate mamba environment
mamba activate rio-simulation

# Navigate to software directory
cd /path/to/open-microfluidics-workstation/software

# Verify dependencies
python -c "import numpy, cv2, flask, flask_socketio; print('All dependencies OK')"
```

**Check Module Enable:**
```bash
# Default: enabled
echo $RIO_DROPLET_ANALYSIS_ENABLED  # Should be empty or "true"

# To disable for testing:
export RIO_DROPLET_ANALYSIS_ENABLED=false
```

### 2. Start the Application

```bash
# Start server (default port 5001)
python main.py

# Or specify port
python main.py 5001
```

**Expected Output:**
- ✅ "Droplet detector controller initialized"
- ✅ "Droplet web controller initialized"
- ✅ Server starts without errors

---

## Test 1: Module Enable/Disable

### Test 1.1: Module Enabled (Default)

**Steps:**
1. Start server: `python main.py`
2. Open browser: `http://<raspberry-pi-ip>:5001`
3. Check navigation tabs

**Expected:**
- ✅ "Droplet Detection" tab visible in navigation
- ✅ Can click on tab and see droplet detection interface
- ✅ Control buttons visible (Start, Stop, Get Status, Export Data)

### Test 1.2: Module Disabled

**Steps:**
1. Set environment variable: `export RIO_DROPLET_ANALYSIS_ENABLED=false`
2. Restart server: `python main.py`
3. Open browser: `http://<raspberry-pi-ip>:5001`

**Expected:**
- ✅ "Droplet Detection" tab NOT visible
- ✅ No errors in console
- ✅ Other tabs work normally

---

## Test 2: Camera Calibration

### Test 2.1: Set Camera Calibration

**Steps:**
1. Start server
2. Open browser to droplet detection tab
3. Set ROI in Camera View tab first
4. Use Python console or API to set calibration:

```python
# Via Python (in separate terminal)
import requests
response = requests.post('http://localhost:5001/api/camera/calibration', 
    json={'um_per_px': 0.82, 'radius_offset_px': -2.0})
print(response.json())
```

**Expected:**
- ✅ Calibration accepted
- ✅ Returns success message
- ✅ Calibration stored in camera

### Test 2.2: Verify Calibration Used

**Steps:**
1. Set calibration (e.g., `um_per_px=0.82`)
2. Start droplet detection
3. Check histogram display

**Expected:**
- ✅ X-axis shows "Size (um)" instead of "Size (px)"
- ✅ Values in histogram are in micrometers
- ✅ Statistics show micrometer values

---

## Test 3: ROI Selection and Detection Start

### Test 3.1: Set ROI and Start Detection

**Steps:**
1. Open Camera View tab
2. Select ROI region (draw rectangle)
3. Switch to Droplet Detection tab
4. Click "Start" button

**Expected:**
- ✅ Status changes to "Running"
- ✅ Frame count starts incrementing
- ✅ Processing rate (Hz) displayed
- ✅ No errors in console

### Test 3.2: Start Without ROI

**Steps:**
1. Do NOT set ROI
2. Go to Droplet Detection tab
3. Click "Start" button

**Expected:**
- ✅ Error message: "Failed to start. Check ROI is set."
- ✅ Status remains "Stopped"
- ✅ No errors in console

---

## Test 4: Real-Time Detection

### Test 4.1: Detection Running

**Steps:**
1. Set ROI and start detection
2. Observe histogram updates
3. Watch statistics panel

**Expected:**
- ✅ Histograms update every ~2 seconds
- ✅ Statistics update every ~2 seconds
- ✅ Processing rate displayed (e.g., "15.23 Hz")
- ✅ Droplet count increases
- ✅ Frame count increases

### Test 4.2: Histogram Display

**Steps:**
1. Let detection run for 30+ seconds
2. Observe histogram charts

**Expected:**
- ✅ Charts maintain fixed aspect ratio (2:1 width:height)
- ✅ Charts start at 0/0 (bottom left)
- ✅ X-axis labeled "Size (um)" or "Size (px)"
- ✅ Y-axis shows integer counts
- ✅ Statistics visible at bottom (not cut off)
- ✅ Charts don't expand downward

### Test 4.3: Statistics Display

**Steps:**
1. Run detection for 1+ minute
2. Check statistics panel

**Expected:**
- ✅ Shows: mean, std, min, max, mode for each metric
- ✅ All values are integers
- ✅ Count is integer
- ✅ Unit displayed (um or px)
- ✅ Processing rate shown (Hz)

---

## Test 5: Stop Detection

### Test 5.1: Stop Button

**Steps:**
1. Start detection
2. Let it run for 10 seconds
3. Click "Stop" button

**Expected:**
- ✅ Status changes to "Stopped"
- ✅ Frame count stops incrementing
- ✅ Processing rate goes to 0.00 Hz
- ✅ No errors

### Test 5.2: Stop via API

**Steps:**
```bash
curl -X POST http://localhost:5001/api/droplet/stop
```

**Expected:**
- ✅ Returns: `{"success": true, "message": "Detection stopped"}`
- ✅ Detection stops in UI

---

## Test 6: Get Status

### Test 6.1: Get Status Button

**Steps:**
1. Start detection
2. Let it run for 10 seconds
3. Click "Get Status" button

**Expected:**
- ✅ Histograms refresh immediately
- ✅ Statistics refresh immediately
- ✅ Status panel updates
- ✅ Shows current frame count, droplet count, processing rate

### Test 6.2: Get Status via API

**Steps:**
```bash
curl http://localhost:5001/api/droplet/status
```

**Expected:**
- ✅ Returns JSON with:
  - `running`: true/false
  - `frame_count`: number
  - `droplet_count_total`: number
  - `processing_rate_hz`: float
  - `statistics`: object with metrics

---

## Test 7: Data Export

### Test 7.1: Export CSV

**Steps:**
1. Start detection
2. Let it run for 30+ seconds (collect data)
3. Click "Export Data" button

**Expected:**
- ✅ File downloads: `droplet_measurements_YYYYMMDD_HHMMSS.csv`
- ✅ File opens in spreadsheet
- ✅ Contains 12 columns:
  - timestamp_ms, frame_id
  - radius_px, radius_um
  - area_px, area_um2
  - x_center_px, y_center_px
  - major_axis_px, major_axis_um
  - equivalent_diameter_px, equivalent_diameter_um
- ✅ All values are numbers (not NaN)

### Test 7.2: Export TXT

**Steps:**
1. Run detection and collect data
2. Use API to export TXT:
```bash
curl -O "http://localhost:5001/api/droplet/export?format=txt"
```

**Expected:**
- ✅ File downloads: `droplet_measurements_YYYYMMDD_HHMMSS.txt`
- ✅ Tab-separated format
- ✅ Same columns as CSV

### Test 7.3: Export with No Data

**Steps:**
1. Don't start detection (or just started)
2. Click "Export Data" button

**Expected:**
- ✅ Error message or no file download
- ✅ No crash

---

## Test 8: Configuration Updates

### Test 8.1: Update Histogram Window Size

**Steps:**
1. Start detection
2. Update config via API:
```bash
curl -X POST http://localhost:5001/api/droplet/config \
  -H "Content-Type: application/json" \
  -d '{"histogram_window_size": 5000, "histogram_bins": 50}'
```

**Expected:**
- ✅ Returns success
- ✅ Histogram window size changes
- ✅ Histogram data may be cleared (by design)
- ✅ New window size used going forward

### Test 8.2: Update Detection Parameters

**Steps:**
```bash
curl -X POST http://localhost:5001/api/droplet/config \
  -H "Content-Type: application/json" \
  -d '{"min_area": 30, "max_area": 3000}'
```

**Expected:**
- ✅ Config updated
- ✅ Detector recreated with new parameters
- ✅ Detection continues with new settings

---

## Test 9: Configuration Profiles

### Test 9.1: Save Profile

**Steps:**
1. Adjust detection parameters
2. Save profile via API:
```bash
curl -X POST http://localhost:5001/api/droplet/profile \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test_profile.json"}'
```

**Expected:**
- ✅ Profile saved to file
- ✅ File contains JSON with all parameters
- ✅ Can open and verify structure

### Test 9.2: Load Profile

**Steps:**
```bash
curl -X POST http://localhost:5001/api/droplet/profile \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test_profile.json"}'
```

**Expected:**
- ✅ Profile loaded
- ✅ Config updated
- ✅ Detector recreated with loaded settings

### Test 9.3: Nested Config Format

**Steps:**
1. Create nested config file:
```json
{
  "modules": {
    "droplet_analysis": true
  },
  "droplet_detection": {
    "histogram_window_size": 3000,
    "histogram_bins": 45,
    "min_area": 25
  }
}
```
2. Save as `test_nested.json`
3. Load via API:
```bash
curl -X POST http://localhost:5001/api/droplet/profile \
  -H "Content-Type: application/json" \
  -d '{"path": "test_nested.json"}'
```

**Expected:**
- ✅ Config loads successfully
- ✅ Parameters extracted correctly
- ✅ Histogram window size = 3000
- ✅ Bins = 45

### Test 9.4: Flat Config Format (Backward Compatibility)

**Steps:**
1. Create flat config file:
```json
{
  "histogram_window_size": 2000,
  "histogram_bins": 40,
  "min_area": 20
}
```
2. Save as `test_flat.json`
3. Load via API

**Expected:**
- ✅ Config loads successfully
- ✅ Works same as nested format
- ✅ Backward compatible

---

## Test 10: WebSocket Commands

### Test 10.1: Start via WebSocket

**Steps:**
1. Open browser console (F12)
2. Execute:
```javascript
socket.emit('droplet', {cmd: 'start'});
```

**Expected:**
- ✅ Detection starts
- ✅ Status updates
- ✅ Histograms begin updating

### Test 10.2: Stop via WebSocket

**Steps:**
```javascript
socket.emit('droplet', {cmd: 'stop'});
```

**Expected:**
- ✅ Detection stops
- ✅ Status updates

### Test 10.3: Get Status via WebSocket

**Steps:**
```javascript
socket.emit('droplet', {cmd: 'get_status'});
```

**Expected:**
- ✅ Receives `droplet:status` event
- ✅ Histograms refresh if running
- ✅ Statistics refresh if running

---

## Test 11: ROI Size Change During Detection

### Test 11.1: Change ROI While Running

**Steps:**
1. Start detection with ROI
2. Let it run for 10 seconds
3. Go to Camera View tab
4. Change ROI size (make it larger or smaller)
5. Return to Droplet Detection tab

**Expected:**
- ✅ No crashes
- ✅ Background resets automatically
- ✅ Detection continues with new ROI
- ✅ May see brief pause while background reinitializes
- ✅ No `cv2.error` about size mismatch

---

## Test 12: Performance Monitoring

### Test 12.1: Processing Rate Display

**Steps:**
1. Start detection
2. Observe processing rate in status panel

**Expected:**
- ✅ Shows rate in Hz (e.g., "15.23 Hz")
- ✅ Updates every ~1 second
- ✅ Rate is reasonable (10-30 Hz typical)
- ✅ Rate decreases if ROI is large

### Test 12.2: Performance API

**Steps:**
```bash
curl http://localhost:5001/api/droplet/performance
```

**Expected:**
- ✅ Returns timing data for:
  - preprocessing
  - segmentation
  - measurement
  - artifact_rejection
  - histogram_update
  - total_per_frame
- ✅ All values in milliseconds
- ✅ Shows mean, min, max for each

---

## Test 13: Reset Functionality

### Test 13.1: Reset Button

**Steps:**
1. Run detection for 30+ seconds
2. Click "Reset" button (if available) or via API:
```bash
curl -X POST http://localhost:5001/api/droplet/reset
```

**Expected:**
- ✅ Histogram cleared
- ✅ Statistics reset to zeros
- ✅ Frame count reset to 0
- ✅ Droplet count reset to 0
- ✅ Raw measurements cleared
- ✅ Detection continues (if running)

---

## Test 14: Error Handling

### Test 14.1: Invalid Config

**Steps:**
```bash
curl -X POST http://localhost:5001/api/droplet/config \
  -H "Content-Type: application/json" \
  -d '{"histogram_window_size": -1}'
```

**Expected:**
- ✅ Returns error or validation warning
- ✅ Config not updated
- ✅ Detection continues with previous config

### Test 14.2: Invalid Export Format

**Steps:**
```bash
curl "http://localhost:5001/api/droplet/export?format=invalid"
```

**Expected:**
- ✅ Returns 400 error
- ✅ Error message: "Format must be 'csv' or 'txt'"

---

## Test 15: Long-Running Session

### Test 15.1: Extended Operation

**Steps:**
1. Start detection
2. Let it run for 10+ minutes
3. Monitor memory usage
4. Check for memory leaks

**Expected:**
- ✅ No memory leaks
- ✅ Histogram stays within window size limit
- ✅ Raw measurements stay within 10,000 limit
- ✅ Processing rate remains stable
- ✅ No crashes or errors

---

## Test 16: Multiple Start/Stop Cycles

### Test 16.1: Repeated Start/Stop

**Steps:**
1. Start detection → Stop (repeat 5 times)
2. Check for errors each time

**Expected:**
- ✅ Each start/stop cycle works
- ✅ No thread leaks
- ✅ No memory buildup
- ✅ Background reinitializes correctly

---

## Test 17: Responsive UI

### Test 17.1: Screen Size Changes

**Steps:**
1. Open droplet detection tab
2. Resize browser window
3. Check histogram layout

**Expected:**
- ✅ Histograms rearrange (side-by-side or stacked)
- ✅ Charts maintain aspect ratio
- ✅ No layout breaks
- ✅ Statistics remain visible

---

## Test 18: Data Accuracy

### Test 18.1: Verify Measurements

**Steps:**
1. Run detection with known test image
2. Export data
3. Compare exported values with visual inspection

**Expected:**
- ✅ Droplet sizes match visual estimate
- ✅ Coordinates match ROI position
- ✅ Units correct (um if calibrated)
- ✅ Values are reasonable

### Test 18.2: Radius Offset Correction

**Steps:**
1. Set `radius_offset_px = -2.0`
2. Run detection
3. Export data
4. Compare with `radius_offset_px = 0.0`

**Expected:**
- ✅ With offset: diameters are 4 pixels smaller (2×offset)
- ✅ Area remains same
- ✅ Correction applied correctly

---

## Test 19: WebSocket Real-Time Updates

### Test 19.1: Histogram Updates

**Steps:**
1. Start detection
2. Monitor WebSocket events in browser console:
```javascript
socket.on('droplet:histogram', (data) => {
    console.log('Histogram update:', data);
});
```

**Expected:**
- ✅ Receives updates every ~2 seconds
- ✅ Data includes histograms for width, height, area, diameter
- ✅ Data includes statistics
- ✅ `pixel_ratio` and `unit` included

### Test 19.2: Statistics Updates

**Steps:**
```javascript
socket.on('droplet:statistics', (data) => {
    console.log('Statistics update:', data);
});
```

**Expected:**
- ✅ Receives updates every ~2 seconds
- ✅ All metrics included (width, height, diameter, area)
- ✅ Values are integers
- ✅ Processing rate included

---

## Test 20: Configuration File Formats

### Test 20.1: Save Nested Format

**Steps:**
1. Update config
2. Save profile with nested=True (via code):
```python
from controllers.droplet_detector_controller import DropletDetectorController
controller.save_profile("test_nested.json", nested=True, include_modules=True)
```

**Expected:**
- ✅ File saved with nested structure
- ✅ Contains `modules.droplet_analysis: true`
- ✅ Contains `droplet_detection` section

### Test 20.2: Save Flat Format

**Steps:**
```python
controller.save_profile("test_flat.json", nested=False)
```

**Expected:**
- ✅ File saved with flat structure
- ✅ All parameters at top level
- ✅ Backward compatible format

---

## Test Checklist Summary

### Basic Functionality
- [ ] Module enable/disable works
- [ ] ROI selection required before start
- [ ] Start/Stop buttons work
- [ ] Status updates correctly
- [ ] Histograms display correctly
- [ ] Statistics display correctly

### Calibration
- [ ] Camera calibration can be set
- [ ] Calibration used in measurements
- [ ] Units display correctly (um/px)
- [ ] Radius offset correction works

### Data Export
- [ ] CSV export works
- [ ] TXT export works
- [ ] Export contains all columns
- [ ] Values are correct
- [ ] Export with no data handled gracefully

### Configuration
- [ ] Config updates work
- [ ] Profile save/load works
- [ ] Nested config format works
- [ ] Flat config format works (backward compatible)
- [ ] Histogram window size configurable

### Performance
- [ ] Processing rate displayed
- [ ] Performance metrics available
- [ ] No memory leaks
- [ ] Stable operation over time

### Error Handling
- [ ] Invalid config rejected
- [ ] Invalid export format rejected
- [ ] ROI changes handled gracefully
- [ ] No crashes on errors

### UI/UX
- [ ] Responsive layout
- [ ] Charts maintain aspect ratio
- [ ] Statistics not cut off
- [ ] Real-time updates work

---

## Expected Performance

### Raspberry Pi 4 (64-bit)
- **Frame Rate:** 20-30 FPS (depending on ROI size)
- **Processing Rate:** 15-25 Hz typical
- **Memory Usage:** ~1-2 MB (default config)

### Raspberry Pi 4 (32-bit)
- **Frame Rate:** 15-25 FPS (depending on ROI size)
- **Processing Rate:** 12-20 Hz typical
- **Memory Usage:** ~1-2 MB (default config)

### Raspberry Pi 3
- **Frame Rate:** 10-15 FPS (depending on ROI size)
- **Processing Rate:** 8-12 Hz typical
- **Memory Usage:** ~1-2 MB (default config)

---

## Troubleshooting

### Issue: Histograms not updating
**Check:**
- Detection is running (status = "Running")
- ROI is set
- WebSocket connection active
- Check browser console for errors

### Issue: Export returns no data
**Check:**
- Detection has been running
- Droplets have been detected
- Check `droplet_count_total` in status

### Issue: Processing rate is 0
**Check:**
- Detection is actually running
- Frames are being processed
- Wait 1-2 seconds for rate calculation

### Issue: Units show "px" instead of "um"
**Check:**
- Camera calibration is set (`um_per_px != 1.0`)
- Calibration retrieved correctly
- Histogram initialized with calibration

---

## Success Criteria

**All tests should:**
- ✅ Complete without crashes
- ✅ Show expected behavior
- ✅ Update UI correctly
- ✅ Handle errors gracefully
- ✅ Maintain performance over time

---

**Last Updated:** December 2025
