# Droplet Detection Deployment Checklist
## Pre-Deployment Verification

**Date:** December 2025  
**Version:** 1.0

---

## Pre-Deployment Checklist

### 1. Environment Setup

- [ ] Mamba environment `rio-simulation` is created and activated
- [ ] All dependencies installed:
  - [ ] OpenCV (`cv2`)
  - [ ] NumPy
  - [ ] Flask
  - [ ] Flask-SocketIO
  - [ ] Pillow (PIL)
- [ ] Python version 3.8+ verified
- [ ] Environment activated: `mamba activate rio-simulation`

**Verification:**
```bash
python -c "import cv2, numpy, flask, flask_socketio; print('✓ All dependencies OK')"
```

### 2. Code Verification

- [ ] All droplet detection modules present in `software/droplet-detection/`
- [ ] Controller files present:
  - [ ] `controllers/droplet_detector_controller.py`
  - [ ] `rio-webapp/controllers/droplet_web_controller.py`
- [ ] Web interface updated:
  - [ ] `rio-webapp/templates/index.html` includes droplet detection tab
  - [ ] `rio-webapp/static/droplet_histogram.js` exists
  - [ ] `rio-webapp/routes.py` includes droplet API endpoints
- [ ] Main application updated:
  - [ ] `main.py` initializes droplet detector

**Verification:**
```bash
cd software
python -c "from droplet_detection import DropletDetector; print('✓ Import OK')"
```

### 3. Testing

- [ ] Unit tests pass:
  ```bash
  python -m unittest discover -s tests -p "test_droplet_detection.py" -v
  ```
- [ ] Integration tests pass (if test images available):
  ```bash
  python -m droplet_detection.test_integration --images 5
  ```
- [ ] No import errors:
  ```bash
  python -c "from controllers.droplet_detector_controller import DropletDetectorController; print('✓ Controller import OK')"
  ```

### 4. Camera System

- [ ] Camera module connected and detected
- [ ] Camera type selected in web interface
- [ ] Camera feed visible in Camera View tab
- [ ] ROI selection working (can draw rectangle on feed)
- [ ] ROI coordinates saved and retrievable

**Verification:**
1. Start application: `python main.py`
2. Open web interface
3. Go to Camera View tab
4. Verify camera feed displays
5. Draw ROI rectangle
6. Verify ROI coordinates appear

### 5. Configuration

- [ ] Default configuration loads correctly
- [ ] Configuration validation works
- [ ] Configuration can be saved/loaded from JSON
- [ ] Parameter profiles can be loaded (if created)

**Verification:**
```bash
python -c "
from droplet_detection import DropletDetectionConfig, load_config, save_config
config = DropletDetectionConfig()
is_valid, errors = config.validate()
print(f'✓ Config valid: {is_valid}')
save_config(config, 'test_config.json')
loaded = load_config('test_config.json')
print(f'✓ Config save/load OK')
"
```

### 6. Performance Baseline

- [ ] Performance benchmarks run successfully:
  ```bash
  python -m droplet_detection.benchmark --iterations 50
  ```
- [ ] Frame rate limits documented
- [ ] Performance acceptable for target use case

**Expected Performance (Raspberry Pi):**
- Small ROI (50×256): 30-50 FPS (low density)
- Medium ROI (100×512): 15-25 FPS (low density)
- Large ROI (150×1024): 5-10 FPS (low density)

### 7. Web Interface

- [ ] Web application starts without errors
- [ ] Droplet Detection tab visible
- [ ] Control buttons functional (Start/Stop/Reset)
- [ ] Histogram visualizations load (Chart.js)
- [ ] WebSocket connection established
- [ ] Real-time updates working

**Verification:**
1. Start application: `python main.py`
2. Open browser: `http://localhost:5000`
3. Navigate to Droplet Detection tab
4. Verify all UI elements visible
5. Check browser console for errors

### 8. API Endpoints

- [ ] REST API endpoints accessible:
  ```bash
  curl http://localhost:5000/api/droplet/status
  ```
- [ ] WebSocket events working
- [ ] Error handling functional

**Test Commands:**
```bash
# Status
curl http://localhost:5000/api/droplet/status

# Start (should return success)
curl -X POST http://localhost:5000/api/droplet/start

# Statistics
curl http://localhost:5000/api/droplet/statistics

# Histogram
curl http://localhost:5000/api/droplet/histogram
```

### 9. Platform Compatibility

- [ ] Tested on target platform (Pi32 or Pi64)
- [ ] Camera abstraction works with target camera type
- [ ] No platform-specific errors
- [ ] Memory usage acceptable

**Platform-Specific Checks:**
- **Pi32:** Verify 32-bit compatibility
- **Pi64:** Verify 64-bit compatibility
- **Camera:** Verify camera type (legacy/v2/mako) works

### 10. Documentation

- [ ] User guide available: `docs/droplet_detection_user_guide.md`
- [ ] Developer guide available: `docs/droplet_detection_developer_guide.md`
- [ ] Testing guide available: `docs/testing_and_optimization_guide.md`
- [ ] README updated with droplet detection info
- [ ] API documentation available

---

## Deployment Steps

### Step 1: Clean Installation Test

1. **On a clean Raspberry Pi:**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd open-microfluidics-workstation
   
   # Create environment
   mamba create -n rio-simulation python=3.10 -y
   mamba activate rio-simulation
   
   # Install dependencies
   cd software
   pip install -r requirements.txt  # Or appropriate requirements file
   ```

2. **Verify installation:**
   ```bash
   python tests/test_imports.py
   python -m droplet_detection.test_integration
   ```

### Step 2: Configuration

1. **Create initial configuration:**
   ```bash
   python -c "
   from droplet_detection import DropletDetectionConfig, save_config
   config = DropletDetectionConfig()
   save_config(config, 'default_config.json')
   "
   ```

2. **Optimize parameters (optional):**
   ```bash
   python -m droplet_detection.optimize --max-images 20
   ```

### Step 3: System Integration

1. **Verify camera system:**
   - Camera detected
   - ROI selection working
   - Frame acquisition working

2. **Test droplet detection:**
   - Set ROI
   - Start detection
   - Verify histograms update
   - Check statistics

### Step 4: Performance Validation

1. **Run benchmarks:**
   ```bash
   python -m droplet_detection.benchmark --iterations 100
   ```

2. **Document results:**
   - Save benchmark results
   - Note frame rate limits
   - Document optimal ROI sizes

### Step 5: Production Deployment

1. **Start application:**
   ```bash
   cd software
   python main.py
   ```

2. **Verify web interface:**
   - All tabs accessible
   - Droplet detection functional
   - Real-time updates working

3. **Monitor performance:**
   - Check frame rate
   - Monitor CPU usage
   - Verify memory usage

---

## Post-Deployment Verification

### Functional Tests

- [ ] Detection starts successfully
- [ ] Droplets detected in test images
- [ ] Histograms update in real-time
- [ ] Statistics calculated correctly
- [ ] Performance metrics available

### Performance Tests

- [ ] Frame rate meets requirements
- [ ] CPU usage acceptable
- [ ] Memory usage stable
- [ ] No memory leaks

### Integration Tests

- [ ] Works with camera system
- [ ] Works with strobe system
- [ ] Web interface responsive
- [ ] API endpoints functional

---

## Troubleshooting Deployment Issues

### Issue: Import Errors

**Symptoms:** `ModuleNotFoundError` when importing droplet detection

**Solutions:**
1. Verify environment activated: `mamba activate rio-simulation`
2. Check Python path: `which python`
3. Verify imports: `python -c "from droplet_detection import DropletDetector"`
4. Check working directory: Run from `software/` directory

### Issue: Camera Not Working

**Symptoms:** No camera feed or detection fails

**Solutions:**
1. Verify camera connected
2. Check camera type selection
3. Verify camera permissions
4. Test camera independently

### Issue: Low Performance

**Symptoms:** Low frame rate or high CPU usage

**Solutions:**
1. Reduce ROI size
2. Optimize parameters
3. Check system load
4. Run benchmarks to identify bottlenecks

### Issue: Web Interface Not Updating

**Symptoms:** Histograms not updating or WebSocket errors

**Solutions:**
1. Check browser console for errors
2. Verify WebSocket connection
3. Check detection is running
4. Verify Chart.js library loaded

---

## Rollback Plan

If deployment fails:

1. **Disable droplet detection:**
   - Comment out droplet detector initialization in `main.py`
   - Application will run without droplet detection

2. **Revert to previous version:**
   ```bash
   git checkout <previous-commit>
   ```

3. **Clean environment:**
   ```bash
   mamba deactivate
   mamba remove -n rio-simulation --all
   mamba create -n rio-simulation python=3.10 -y
   # Reinstall dependencies
   ```

---

## Maintenance

### Regular Checks

- [ ] Monitor performance metrics
- [ ] Check for memory leaks
- [ ] Verify detection accuracy
- [ ] Update parameters if needed

### Updates

- [ ] Keep dependencies updated
- [ ] Test new features before deployment
- [ ] Maintain documentation
- [ ] Backup configurations

---

## Support Resources

- **User Guide:** `docs/droplet_detection_user_guide.md`
- **Developer Guide:** `docs/droplet_detection_developer_guide.md`
- **Testing Guide:** `docs/testing_and_optimization_guide.md`
- **Roadmap:** `docs/droplet_detection_development_roadmap_v2.md`

---

**Status:** ✅ Deployment checklist complete

**Last Updated:** December 2025
