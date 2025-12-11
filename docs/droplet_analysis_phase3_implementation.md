# Droplet Analysis Phase 3 Implementation
## Data Export Functionality

**Date:** December 2025

---

## Overview

Phase 3 implements data export functionality:
1. Store raw droplet measurements with timestamps
2. Export endpoint (GET /api/droplet/export)
3. CSV/TXT export format
4. Export button in UI

---

## Implementation Details

### 1. Raw Measurements Storage

**Changes Made:**

#### `controllers/droplet_detector_controller.py`
- Added `raw_measurements` list to store all measurements
- Added `max_raw_measurements = 10000` to limit memory usage
- Added `_store_raw_measurements()` method to store measurements after processing

**Storage Format:**
Each measurement is stored as a dictionary with:
```python
{
    "timestamp_ms": int,  # Milliseconds since epoch
    "frame_id": int,      # Frame number
    "radius_px": float,   # Radius in pixels
    "radius_um": float,   # Radius in micrometers
    "area_px": float,     # Area in pixels²
    "area_um2": float,    # Area in micrometers²
    "x_center_px": float, # X centroid in pixels
    "y_center_px": float, # Y centroid in pixels
    "major_axis_px": float,      # Major axis in pixels
    "major_axis_um": float,      # Major axis in micrometers
    "equivalent_diameter_px": float,  # Equivalent diameter in pixels
    "equivalent_diameter_um": float,  # Equivalent diameter in micrometers
}
```

**Memory Management:**
- Stores up to 10,000 measurements
- When limit reached, removes oldest (keeps most recent)
- Prevents memory buildup during long sessions

**Storage Trigger:**
- Called automatically after each frame is processed
- Stores all droplets detected in that frame
- Uses current timestamp and frame ID

---

### 2. Export Data Method

**Implementation:**

#### `controllers/droplet_detector_controller.py`
- Added `export_data(format_type: str = "csv")` method
- Supports CSV and TXT formats
- Uses Python built-in `csv` module (no heavy dependencies)

**CSV Format:**
- Comma-separated values
- Standard CSV format
- Headers in first row
- Compatible with Excel, Python pandas, etc.

**TXT Format:**
- Tab-separated values
- Plain text format
- Headers in first row
- Compatible with text editors, spreadsheets

**Columns Exported:**
1. `timestamp_ms` - Timestamp in milliseconds
2. `frame_id` - Frame number
3. `radius_px` - Radius in pixels
4. `radius_um` - Radius in micrometers
5. `area_px` - Area in pixels²
6. `area_um2` - Area in micrometers²
7. `x_center_px` - X centroid coordinate
8. `y_center_px` - Y centroid coordinate
9. `major_axis_px` - Major axis in pixels
10. `major_axis_um` - Major axis in micrometers
11. `equivalent_diameter_px` - Equivalent diameter in pixels
12. `equivalent_diameter_um` - Equivalent diameter in micrometers

---

### 3. Export Endpoint

**Implementation:**

#### `rio-webapp/routes.py`
- Added `_register_droplet_export_route()` function
- Route: `GET /api/droplet/export?format=csv`
- Query parameter: `format` (default: "csv", options: "csv" or "txt")
- Returns file download with appropriate MIME type
- Filename includes timestamp: `droplet_measurements_YYYYMMDD_HHMMSS.csv`

**Response:**
- **Success:** File download with CSV/TXT content
- **No data:** 404 error with JSON message
- **Invalid format:** 400 error with JSON message
- **Error:** 500 error with error message

**MIME Types:**
- CSV: `text/csv`
- TXT: `text/plain`

---

### 4. Export Button in UI

**Changes Made:**

#### `rio-webapp/templates/index.html`
- Added "Export Data" button next to other control buttons
- Button uses Bootstrap primary style
- Icon: `bi-download`

#### `rio-webapp/static/droplet_histogram.js`
- Added `exportData(format)` method to `DropletDetectionControls` class
- Creates temporary download link
- Triggers browser download
- Supports format selection (default: CSV)

**Button Location:**
- In control button group
- After "Get Status" button
- Styled consistently with other buttons

---

## Usage

### Via UI Button

1. **Start detection** and let it run
2. **Click "Export Data" button**
3. **File downloads** automatically:
   - Filename: `droplet_measurements_YYYYMMDD_HHMMSS.csv`
   - Format: CSV (default)

### Via API

**CSV Export:**
```bash
curl -O "http://localhost:5001/api/droplet/export?format=csv"
```

**TXT Export:**
```bash
curl -O "http://localhost:5001/api/droplet/export?format=txt"
```

**JavaScript:**
```javascript
// Export as CSV
window.location.href = '/api/droplet/export?format=csv';

// Export as TXT
window.location.href = '/api/droplet/export?format=txt';
```

---

## Export File Format

### CSV Example

```csv
timestamp_ms,frame_id,radius_px,radius_um,area_px,area_um2,x_center_px,y_center_px,major_axis_px,major_axis_um,equivalent_diameter_px,equivalent_diameter_um
1733856000000,1,15.5,12.71,754.0,506.28,100.5,200.3,31.0,25.42,31.0,25.42
1733856000100,2,16.2,13.28,824.0,553.12,150.2,180.7,32.4,26.56,32.4,26.56
```

### TXT Example

```
timestamp_ms	frame_id	radius_px	radius_um	area_px	area_um2	x_center_px	y_center_px	major_axis_px	major_axis_um	equivalent_diameter_px	equivalent_diameter_um
1733856000000	1	15.5	12.71	754.0	506.28	100.5	200.3	31.0	25.42	31.0	25.42
1733856000100	2	16.2	13.28	824.0	553.12	150.2	180.7	32.4	26.56	32.4	26.56
```

---

## Memory Considerations

### Storage Limits

- **Maximum measurements:** 10,000
- **Estimated memory:** ~1-2 MB (depending on droplet count)
- **Automatic cleanup:** Oldest measurements removed when limit reached

### Performance Impact

- **Storage overhead:** Minimal (~100 bytes per measurement)
- **Export overhead:** Negligible (in-memory string generation)
- **No disk I/O during operation:** All data in memory until export

---

## Data Accuracy

### Timestamps

- **Format:** Milliseconds since Unix epoch
- **Precision:** Millisecond-level
- **Synchronization:** Same timestamp for all droplets in same frame

### Measurements

- **Units:** Both pixels and micrometers included
- **Precision:** 2 decimal places
- **Calibration:** Uses current `um_per_px` value
- **Offset correction:** Already applied (from Phase 1)

---

## Testing

### Test Export Functionality

1. **Start detection:**
   - Set ROI
   - Start detection
   - Let it process some frames

2. **Export data:**
   - Click "Export Data" button
   - Verify file downloads

3. **Verify content:**
   - Open CSV file in spreadsheet
   - Check headers are correct
   - Verify data matches displayed statistics
   - Check timestamps are sequential

4. **Test formats:**
   - Export as CSV
   - Export as TXT
   - Verify both work correctly

### Test Memory Management

1. **Run detection for extended period:**
   - Process many frames
   - Verify storage doesn't exceed limit
   - Check oldest measurements are removed

2. **Export after limit:**
   - Verify export contains most recent 10,000 measurements
   - Check no data loss in export

---

## Files Modified

1. **`controllers/droplet_detector_controller.py`**
   - Added `raw_measurements` storage
   - Added `_store_raw_measurements()` method
   - Added `export_data()` method
   - Updated `reset()` to clear measurements

2. **`rio-webapp/routes.py`**
   - Added `_register_droplet_export_route()` function
   - Registered export route in API routes

3. **`rio-webapp/templates/index.html`**
   - Added "Export Data" button

4. **`rio-webapp/static/droplet_histogram.js`**
   - Added `exportData()` method to controls class

---

## API Documentation

### GET /api/droplet/export

**Description:** Export raw droplet measurements as CSV or TXT file.

**Query Parameters:**
- `format` (optional): Export format. Default: "csv". Options: "csv", "txt"

**Response:**
- **200 OK:** File download (CSV or TXT)
- **400 Bad Request:** Invalid format parameter
- **404 Not Found:** No data available for export
- **500 Internal Server Error:** Server error

**Example:**
```
GET /api/droplet/export?format=csv
Content-Type: text/csv
Content-Disposition: attachment; filename=droplet_measurements_20251210_143022.csv
```

---

## Limitations

### Storage Limit

- Maximum 10,000 measurements stored
- Older measurements are automatically removed
- For longer sessions, export periodically

### Memory Usage

- ~100 bytes per measurement
- 10,000 measurements ≈ 1 MB
- Acceptable for Raspberry Pi

### Export Size

- Large exports may take time to generate
- Browser download may be slow for very large files
- Consider exporting periodically for long sessions

---

## Future Enhancements

### Potential Improvements

1. **Configurable storage limit:**
   - Allow user to set `max_raw_measurements`
   - Balance memory vs. data retention

2. **Export filters:**
   - Filter by time range
   - Filter by size range
   - Filter by frame range

3. **Export formats:**
   - JSON format
   - Excel format (xlsx)
   - HDF5 for large datasets

4. **Streaming export:**
   - For very large datasets
   - Stream directly to file

---

## Status

✅ **Raw measurements storage:** Implemented  
✅ **Export endpoint:** Implemented  
✅ **CSV/TXT export:** Implemented  
✅ **Export button:** Implemented  
⏳ **Testing:** Pending  
⏳ **Documentation:** Complete  

---

**Last Updated:** December 2025
