# Droplet Measurement Methods - Detailed Explanation
## How Measurement Works and Test Results

**Date:** December 2025

---

## Overview

The measurement system calculates geometric properties of detected droplets from image contours. This document explains how each metric is calculated and verifies accuracy through comprehensive tests.

---

## Measurement Workflow

### Input: Contours

Contours are detected from binary masks using `cv2.findContours()`. Each contour is a numpy array of points representing the boundary of a detected droplet.

**Format:** `List[np.ndarray]` where each array has shape `(N, 1, 2)` containing `(x, y)` coordinates.

### Processing Steps

For each contour, the following metrics are calculated:

1. **Area** (pixels²)
2. **Bounding Box** (x, y, width, height)
3. **Centroid** (center of mass)
4. **Major Axis** (longest dimension)
5. **Equivalent Diameter** (diameter of circle with same area)
6. **Radius Offset Correction** (applied to diameter and major axis)

---

## Detailed Metric Explanations

### 1. Area (`area`)

**Method:** `cv2.contourArea(contour)`

**What it measures:**
- Total pixel area enclosed by the contour
- Units: pixels²

**Characteristics:**
- Direct measurement from contour
- **NOT affected by radius offset correction**
- Most accurate for irregular shapes

**Example:**
- Circle with radius 30 px → Area ≈ 2736 px² (π × 30² ≈ 2827, but pixel discretization gives 2736)

---

### 2. Bounding Box (`bounding_box`)

**Method:** `cv2.boundingRect(contour)`

**What it measures:**
- Smallest axis-aligned rectangle that encloses the contour
- Returns: `(x, y, width, height)`
  - `x, y`: Top-left corner coordinates
  - `width, height`: Rectangle dimensions

**Use cases:**
- Spatial filtering
- Aspect ratio calculation
- Fallback for ellipse fitting

**Example:**
- Circle at (100, 100) with radius 30 → Bounding box: `(70, 70, 61, 61)`

---

### 3. Centroid (`centroid`)

**Method:** Image moments (`cv2.moments()`)

**What it measures:**
- Center of mass of the contour
- Calculated from: `cx = M10/M00`, `cy = M01/M00`
- Returns: `(cx, cy)` coordinates

**Accuracy:**
- Very accurate for symmetric shapes
- Slight pixel discretization error for asymmetric shapes

**Test Result:**
- Circle at (100, 100) → Centroid: `(100.0, 100.0)` ✓

---

### 4. Major Axis (`major_axis`)

**Method:** Ellipse fitting (`cv2.fitEllipse()`)

**What it measures:**
- Longest dimension of the droplet
- Fits an ellipse to the contour and takes the maximum of (width, height)
- Units: pixels

**Fallback behavior:**
- If ellipse fitting fails or contour has < 5 points:
  - Falls back to `max(bounding_box_width, bounding_box_height)`

**Radius offset correction:**
- ✅ **IS corrected** with `radius_offset_px`
- Applied as: `corrected_major_axis = 2 * (major_axis_radius + offset)`

**Test Result:**
- Circle with radius 30 px → Major axis: 59.08 px
- With offset -2.0 px → Major axis: 55.08 px (difference: 4.0 px = 2 × offset) ✓

---

### 5. Equivalent Diameter (`equivalent_diameter`)

**Method:** Mathematical formula

**Formula:**
```
equivalent_diameter = sqrt(4 × area / π)
```

**What it measures:**
- Diameter of a circle with the same area as the contour
- Useful for comparing droplets of different shapes
- Units: pixels

**Why it's useful:**
- Normalizes area to a linear dimension
- Easier to interpret than area
- Standard metric in droplet analysis

**Radius offset correction:**
- ✅ **IS corrected** with `radius_offset_px`
- Applied as:
  ```
  raw_radius = equivalent_diameter / 2
  corrected_radius = raw_radius + radius_offset_px
  corrected_diameter = corrected_radius × 2
  ```

**Test Results:**
- Circle with radius 30 px:
  - Area: 2736 px²
  - Equivalent diameter: 59.02 px (matches `sqrt(4 × 2736 / π)`)
  - Measured radius: 29.51 px (close to true 30 px)
  
- With offset -2.0 px:
  - Diameter: 55.02 px (reduced by 4.0 px = 2 × offset) ✓

---

### 6. Radius Offset Correction

**Purpose:**
- Corrects for systematic threshold bias in segmentation
- Thresholding may produce droplets slightly too large or small
- Offset is determined by comparing detected size to known true size

**How it works:**

1. **Calculate raw radius:**
   ```python
   raw_radius = diameter / 2.0
   ```

2. **Apply offset:**
   ```python
   corrected_radius = raw_radius + radius_offset_px
   # Ensure non-negative
   corrected_radius = max(0.0, corrected_radius)
   ```

3. **Convert back to diameter:**
   ```python
   corrected_diameter = corrected_radius × 2.0
   ```

**Applied to:**
- ✅ `equivalent_diameter`
- ✅ `major_axis`
- ❌ `area` (NOT affected - direct measurement)
- ❌ `centroid` (NOT affected - position only)
- ❌ `bounding_box` (NOT affected - spatial reference)

**Test Verification:**

| Test Case | Offset | Diameter Change | Expected | Actual | Status |
|-----------|--------|-----------------|----------|--------|--------|
| Negative offset | -2.0 px | Should decrease by 4.0 px | 4.0 px | 4.0 px | ✅ |
| Positive offset | +2.0 px | Should increase by 4.0 px | 4.0 px | 4.0 px | ✅ |
| Major axis | -2.0 px | Should decrease by 4.0 px | 4.0 px | 4.0 px | ✅ |

**Example Calculation:**

For a droplet with:
- Raw equivalent diameter: 60.0 px
- Radius offset: -2.0 px

```
raw_radius = 60.0 / 2 = 30.0 px
corrected_radius = 30.0 + (-2.0) = 28.0 px
corrected_diameter = 28.0 × 2 = 56.0 px
```

Difference: 60.0 - 56.0 = 4.0 px = 2 × |offset| ✓

---

## Test Results Summary

### All Tests Passed ✅

**Test Suite:** 10 tests, 0 failures, 0 errors

**Key Test Results:**

1. **Measurement Workflow:**
   - ✅ All metrics calculated correctly
   - ✅ Circle with radius 30 px measured accurately

2. **Radius Offset Correction:**
   - ✅ Negative offset reduces diameter correctly
   - ✅ Positive offset increases diameter correctly
   - ✅ Offset applied to both `equivalent_diameter` and `major_axis`
   - ✅ Area preserved (not affected by offset)

3. **Formula Verification:**
   - ✅ Equivalent diameter = `sqrt(4 × area / π)` ✓
   - ✅ Centroid calculation accurate
   - ✅ Ellipse fitting fallback works

4. **Edge Cases:**
   - ✅ Negative radius protection (prevents negative diameters)
   - ✅ Multiple contours handled correctly
   - ✅ Zero-area contours skipped

---

## Measurement Accuracy

### Pixel Discretization Effects

**Observed:**
- Perfect circle with radius 30 px:
  - True area: π × 30² = 2827.43 px²
  - Measured area: 2736 px² (pixel discretization)
  - Measured diameter: 59.02 px (vs true 60 px)
  - Error: ~1.6% (acceptable for pixel-based measurement)

**Why:**
- Pixels are discrete units
- Circle boundary is approximated by pixels
- Area and diameter measurements reflect this approximation

### Accuracy with Offset Correction

**Test Results:**
- Offset correction is mathematically exact
- Difference always equals `2 × |offset|` for diameter
- No additional error introduced by correction

---

## Practical Usage

### Setting Radius Offset

**Calibration Procedure:**

1. **Capture image of reference object:**
   - Known size (e.g., calibration bead: 50 µm diameter)

2. **Measure in pixels:**
   - Use Fiji/ImageJ or detection system
   - Example: Detected diameter = 52 px

3. **Calculate offset:**
   ```
   true_radius_px = (true_size_um / um_per_px) / 2
   detected_radius_px = detected_diameter / 2
   radius_offset_px = true_radius_px - detected_radius_px
   ```

4. **Example:**
   - True size: 50 µm
   - Calibration: 0.82 µm/px
   - True radius: (50 / 0.82) / 2 = 30.49 px
   - Detected radius: 52 / 2 = 26 px
   - Offset: 30.49 - 26 = 4.49 px (positive, increases size)

**Apply in code:**
```python
camera.set_calibration(um_per_px=0.82, radius_offset_px=4.49)
```

---

## Code Flow Diagram

```
Contour (from segmentation)
    ↓
┌─────────────────────────────────┐
│ 1. Calculate Area               │ → area (pixels²)
│    cv2.contourArea()            │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 2. Get Bounding Box             │ → bounding_box (x, y, w, h)
│    cv2.boundingRect()           │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 3. Calculate Centroid            │ → centroid (cx, cy)
│    cv2.moments()                │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 4. Fit Ellipse                  │ → major_axis (pixels)
│    cv2.fitEllipse()             │   (or fallback to bbox)
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 5. Calculate Equivalent Diameter│ → equivalent_diameter (pixels)
│    sqrt(4 × area / π)           │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 6. Apply Radius Offset          │ → Corrected diameters
│    corrected_radius =           │
│      raw_radius + offset        │
└─────────────────────────────────┘
    ↓
DropletMetrics object
```

---

## Key Insights

### 1. Area is Most Accurate
- Direct pixel count
- Not affected by shape approximation
- Use for area-based filtering

### 2. Equivalent Diameter is Most Useful
- Normalizes shape differences
- Easy to interpret
- Standard metric in literature
- **Corrected with offset** for accuracy

### 3. Major Axis Shows Orientation
- Longest dimension
- Useful for non-circular droplets
- **Also corrected with offset**

### 4. Offset Correction is Exact
- Mathematical operation (no approximation)
- Applied consistently to all radius-based metrics
- Does not introduce additional error

---

## Recommendations

### For Best Accuracy:

1. **Calibrate regularly:**
   - Use reference objects
   - Verify offset periodically

2. **Use equivalent diameter:**
   - Most reliable metric
   - Already corrected with offset

3. **Monitor area separately:**
   - Not affected by offset
   - Good for validation

4. **Check centroid accuracy:**
   - Should be stable for symmetric droplets
   - Large deviations indicate detection issues

---

## Test Coverage

✅ **Workflow verification** - All steps work correctly  
✅ **Offset correction** - Negative and positive offsets  
✅ **Formula accuracy** - Equivalent diameter formula verified  
✅ **Edge cases** - Negative radius protection, multiple contours  
✅ **Metric preservation** - Area not affected by offset  
✅ **Major axis correction** - Offset applied correctly  

**All tests passed with 100% success rate.**

---

## Conclusion

The measurement methods are:
- ✅ **Accurate** - Verified with known shapes
- ✅ **Robust** - Handles edge cases
- ✅ **Correct** - Offset correction works exactly as designed
- ✅ **Well-tested** - Comprehensive test coverage

The radius offset correction successfully addresses threshold bias while maintaining measurement accuracy.

---

**Last Updated:** December 2025
