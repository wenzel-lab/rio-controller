# Droplet Detection User Guide
## Open Microfluidics Workstation

**Version:** 1.0  
**Date:** December 2025

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Using the Web Interface](#using-the-web-interface)
6. [Parameter Tuning](#parameter-tuning)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tips](#performance-tips)

---

## Introduction

The droplet detection system provides real-time detection and analysis of microfluidic droplets using classical computer vision techniques. It is designed to run efficiently on Raspberry Pi hardware (both 32-bit and 64-bit) and provides:

- **Real-time detection** of droplets in microfluidic channels
- **Histogram visualization** of droplet size distributions
- **Statistics** (mean, std, mode, min, max) for width, height, area, and diameter
- **Web-based interface** for monitoring and control
- **REST API** for programmatic access
- **Performance monitoring** with timing metrics

---

## Installation

### Prerequisites

- Raspberry Pi (32-bit or 64-bit OS)
- Camera module (PiCamera Legacy, PiCamera V2, or Mako camera)
- Mamba/Conda environment manager
- Python 3.8+

### Environment Setup

1. **Activate the mamba environment:**
   ```bash
   mamba activate rio-simulation
   ```

2. **Verify dependencies:**
   ```bash
   python -c "import cv2, numpy, flask, flask_socketio"
   ```

   If any imports fail, install missing packages:
   ```bash
   mamba install opencv numpy flask flask-socketio
   ```

### Verify Installation

Run the integration tests to verify everything is working:

```bash
cd software
python -m droplet_detection.test_integration --images 5
```

---

## Quick Start

### 1. Start the Web Application

```bash
cd software
python main.py
```

The web interface will be available at `http://localhost:5000` (or your Pi's IP address).

### 2. Set Up Camera and ROI

1. Open the web interface in your browser
2. Go to the **Camera View** tab
3. Select your camera type (if not already selected)
4. Draw a **Region of Interest (ROI)** on the camera feed:
   - Click and drag to draw a rectangle
   - The ROI should cover the microfluidic channel where droplets flow
   - Smaller ROI = faster processing

### 3. Start Detection

1. Go to the **Droplet Detection** tab
2. Click **Start Detection**
3. View real-time histograms and statistics

### 4. Monitor Results

- **Histograms** show size distributions for width, height, area, and diameter
- **Statistics** display mean, std, mode, min, max for each metric
- **Status** shows frame count and total droplets detected

---

## Configuration

### Default Configuration

The system uses sensible defaults, but you can customize parameters for your specific setup.

### Configuration Parameters

Key parameters (see `DropletDetectionConfig` for full list):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_area` | 20 | Minimum droplet area (pixels²) |
| `max_area` | 10000 | Maximum droplet area (pixels²) |
| `threshold_method` | "otsu" | Thresholding method ("otsu" or "adaptive") |
| `background_method` | "static" | Background correction ("static" or "highpass") |
| `morph_kernel_size` | 5 | Morphological operation kernel size |
| `histogram_window_size` | 1000 | Number of droplets in histogram window |

### Loading a Configuration

**Via Web Interface:**
1. Go to Droplet Detection tab
2. Use WebSocket command:
   ```javascript
   socket.emit('droplet', {
       cmd: 'profile',
       parameters: { path: '/path/to/config.json' }
   });
   ```

**Via REST API:**
```bash
curl -X POST http://localhost:5000/api/droplet/profile \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/config.json"}'
```

**Programmatically:**
```python
from droplet_detection import load_config, DropletDetector

config = load_config('my_config.json')
detector = DropletDetector(config)
```

### Creating a Custom Configuration

1. Start with default config:
   ```python
   from droplet_detection import DropletDetectionConfig, save_config
   
   config = DropletDetectionConfig()
   config.min_area = 30
   config.max_area = 5000
   save_config(config, 'my_config.json')
   ```

2. Or modify existing:
   ```python
   from droplet_detection import load_config, save_config
   
   config = load_config('default_config.json')
   config.update({'min_area': 30, 'max_area': 5000})
   save_config(config, 'my_config.json')
   ```

---

## Using the Web Interface

### Droplet Detection Tab

**Controls:**
- **Start Detection**: Begin processing frames
- **Stop Detection**: Pause processing
- **Reset**: Clear histogram and statistics
- **Get Status**: Refresh status display

**Visualizations:**
- **Histograms**: Real-time bar charts for width, height, area, diameter
- **Statistics**: Text display of mean, std, mode, min, max
- **Status**: Running state, frame count, total droplets

### REST API Endpoints

All endpoints return JSON:

**Status:**
```bash
GET /api/droplet/status
```

**Control:**
```bash
POST /api/droplet/start
POST /api/droplet/stop
```

**Data:**
```bash
GET /api/droplet/histogram
GET /api/droplet/statistics
GET /api/droplet/performance
```

**Configuration:**
```bash
POST /api/droplet/config
# Body: {"min_area": 30, "max_area": 5000, ...}

POST /api/droplet/profile
# Body: {"path": "/path/to/config.json"}
```

### WebSocket Events

**Client → Server:**
```javascript
// Start detection
socket.emit('droplet', { cmd: 'start' });

// Update configuration
socket.emit('droplet', {
    cmd: 'config',
    parameters: { min_area: 30, max_area: 5000 }
});
```

**Server → Client:**
```javascript
// Listen for updates
socket.on('droplet:histogram', (data) => {
    console.log('Histogram:', data);
});

socket.on('droplet:statistics', (data) => {
    console.log('Statistics:', data);
});

socket.on('droplet:status', (data) => {
    console.log('Status:', data);
});
```

---

## Parameter Tuning

### Finding Optimal Parameters

Use the optimization tool to find best parameters for your setup:

```bash
cd software
python -m droplet_detection.optimize \
    --dataset /path/to/test/images \
    --max-images 30 \
    --output optimized_config.json
```

This will:
1. Test multiple parameter combinations
2. Evaluate on your test images
3. Rank configurations by performance
4. Save top configurations

### Manual Tuning Guide

**1. Adjust Area Filters:**
- **Too many false positives?** Increase `min_area`
- **Missing small droplets?** Decrease `min_area`
- **Missing large droplets?** Increase `max_area`

**2. Threshold Method:**
- **Otsu**: Good for uniform illumination
- **Adaptive**: Better for varying illumination

**3. Background Correction:**
- **Static**: Fast, good for stable background
- **High-pass**: Better for slowly varying background

**4. Morphological Operations:**
- Larger `morph_kernel_size`: More smoothing, slower
- Smaller: Faster, less smoothing

### Testing Parameters

1. Use test images from your experiments
2. Run detection with different parameters
3. Compare results visually
4. Use optimization tool for systematic search

---

## Troubleshooting

### Detection Not Starting

**Problem:** "Failed to start. Check ROI is set."

**Solution:**
1. Go to Camera View tab
2. Draw ROI on camera feed
3. Verify ROI is visible (green rectangle)
4. Try starting detection again

### No Droplets Detected

**Possible Causes:**
1. **ROI not covering channel:**
   - Adjust ROI to cover droplet flow path
   
2. **Area filters too restrictive:**
   - Decrease `min_area`
   - Increase `max_area`
   
3. **Threshold too high/low:**
   - Try different `threshold_method`
   - Adjust threshold parameters

4. **Illumination issues:**
   - Check camera exposure
   - Try `background_method: "highpass"`

### Poor Performance (Low Frame Rate)

**Solutions:**
1. **Reduce ROI size:**
   - Smaller ROI = faster processing
   - Aim for 50-256 px width

2. **Optimize parameters:**
   - Use `threshold_method: "otsu"` (faster than adaptive)
   - Use `background_method: "static"` (faster than highpass)
   - Reduce `morph_kernel_size`

3. **Check system load:**
   - Monitor CPU usage
   - Close other applications

### Histogram Not Updating

**Problem:** Histograms show no data

**Solutions:**
1. Verify detection is running (check status)
2. Check that droplets are being detected (frame count should increase)
3. Try resetting (Reset button)
4. Check browser console for WebSocket errors

### Camera Not Working

**Problem:** No camera feed or "Camera disabled"

**Solutions:**
1. Check camera is connected
2. Select correct camera type in Camera Config tab
3. Verify camera permissions
4. Check camera is not used by another process

---

## Performance Tips

### Optimal ROI Size

- **Small (50×256 px):** Fastest, good for single channel
- **Medium (100×512 px):** Balanced, good for multiple channels
- **Large (150×1024 px):** Slower, use only if necessary

### Frame Rate Expectations

Typical performance on Raspberry Pi:

| ROI Size | Droplets/Frame | Expected FPS |
|----------|----------------|--------------|
| Small    | 1-5            | 30-50        |
| Small    | 5-20           | 20-30        |
| Medium   | 1-5            | 15-25        |
| Medium   | 5-20           | 10-15        |
| Large    | 1-5            | 5-10         |

*Actual performance depends on Pi model and system load*

### Benchmarking Your Setup

Run performance benchmarks:

```bash
cd software
python -m droplet_detection.benchmark \
    --roi-size medium \
    --density medium \
    --iterations 200
```

This will show:
- Component-level timing
- Frame rate limits
- Performance recommendations

### Memory Management

- Histogram window size affects memory usage
- Default (1000 droplets) uses ~1-2 MB
- Reduce `histogram_window_size` if memory constrained

---

## Advanced Usage

### Programmatic Access

```python
from controllers.droplet_detector_controller import DropletDetectorController
from controllers.camera import Camera
from controllers.strobe_cam import PiStrobeCam

# Initialize
camera = Camera(exit_event, socketio)
strobe_cam = PiStrobeCam(...)
controller = DropletDetectorController(camera, strobe_cam)

# Start detection
controller.start()

# Get statistics
stats = controller.get_statistics()
print(stats)

# Get histogram
hist = controller.get_histogram()
print(hist)

# Get performance metrics
perf = controller.get_performance_metrics()
print(perf)
```

### Custom Processing

You can extend the detection pipeline:

```python
from droplet_detection import DropletDetector, DropletDetectionConfig

config = DropletDetectionConfig()
detector = DropletDetector(config)

# Process single frame
metrics = detector.process_frame(frame)

# Access individual components
preprocessor = detector.preprocessor
segmenter = detector.segmenter
measurer = detector.measurer
```

---

## Support

- **Documentation:** See `docs/` directory
- **Issues:** Open an issue on GitHub
- **Testing:** Run `python -m droplet_detection.test_integration`
- **Benchmarking:** See `docs/testing_and_optimization_guide.md`

---

## Next Steps

1. **Optimize parameters** for your specific setup
2. **Run benchmarks** to establish performance baseline
3. **Monitor performance** during experiments
4. **Save configurations** for different experimental conditions

For more information, see:
- `docs/testing_and_optimization_guide.md` - Testing and optimization
- `docs/droplet_detection_development_roadmap_v2.md` - Technical details
- `software/droplet-detection/` - Source code

---

**Last Updated:** December 2025
