# Rio Controller Simulation Guide

## Overview

The Rio controller now supports **simulation mode**, allowing you to develop and test the software on your Mac or PC without requiring physical Raspberry Pi hardware or connected modules.

This follows the **Wenzel-Lab repository template** patterns for modular, abstracted code with simulation capabilities.

**Note:** This development aligns with the IIBM proposal requirements for Raspberry Pi and desktop compatibility, simple solutions, and Flask-based interfaces. See `PROJECT_ALIGNMENT.md` for details.

---

## Getting Started: Complete Setup Guide

### Step 1: Navigate to Repository

Open your terminal and navigate to the repository:

```bash
cd ~/Documents/GitHub/open-microfluidics-workstation
```

Or if your repository is in a different location:

```bash
cd /path/to/your/open-microfluidics-workstation
```

**Verify you're in the right place:**
```bash
ls -la
# You should see: user-interface-software/, rio-config.yaml, etc.
```

---

### Step 2: Set Up Mamba Environment

#### 2.1 Create Mamba Environment

Create a new mamba environment with Python 3.9 or 3.10 (recommended):

```bash
mamba create -n rio-simulation python=3.10 -y
```

**Note:** If you don't have mamba installed, you can use conda instead:
```bash
conda create -n rio-simulation python=3.10 -y
```

#### 2.2 Activate Environment

Activate the environment:

```bash
mamba activate rio-simulation
```

Or with conda:
```bash
conda activate rio-simulation
```

**Verify activation:**
```bash
which python
# Should show: .../mamba/envs/rio-simulation/bin/python
```

---

### Step 3: Install Dependencies

#### 3.1 Navigate to Requirements File

```bash
cd user-interface-software/src
```

#### 3.2 Install Core Dependencies

For **simulation mode** (Mac/PC), you don't need Raspberry Pi-specific packages. Install the core dependencies:

```bash
# Core web framework and dependencies (Python 3.10 compatible versions)
pip install "Flask>=2.0.0,<3.0.0" "Flask-SocketIO>=5.0.0" "Werkzeug>=2.0.0,<3.0.0" eventlet

# Image processing (for simulated camera)
pip install opencv-python numpy Pillow

# Configuration file support
pip install PyYAML

# WebSocket support
pip install "python-socketio>=5.0.0"
```

**Or install from the provided requirements file:**

The repository includes `requirements-simulation.txt` with Python 3.10+ compatible versions:

```bash
# Install from requirements file
pip install -r requirements-simulation.txt
```

This file uses updated package versions that are compatible with Python 3.10+.

**Note:** We're **skipping** `spidev`, `RPi.GPIO`, and `picamera` because:
- `spidev` - Only needed for real Raspberry Pi SPI
- `RPi.GPIO` - Only needed for real Raspberry Pi GPIO
- `picamera` - Only needed for real Raspberry Pi camera

The simulation module provides mock implementations instead.

#### 3.3 Verify Installation

Test that key packages are installed:

```bash
python -c "import flask; import cv2; import numpy; import yaml; print('All packages installed!')"
```

---

### Step 4: Configure Simulation Mode

#### 4.1 Configuration Options

The simulation system supports **two ways** to enable simulation:

**Option A: Environment Variable (Simplest - Recommended)**
```bash
export RIO_SIMULATION=true
```
This is the easiest method and works immediately.

**Option B: YAML Configuration File (Optional)**

If you want to use a YAML config file, you can create `rio-config.yaml` in the repository root:

```bash
cd ~/Documents/GitHub/open-microfluidics-workstation  # Back to repo root

# Create config file (if it doesn't exist)
cat > rio-config.yaml << 'EOF'
simulation: true
camera:
  width: 640
  height: 480
  fps: 30
  generate_droplets: true
  droplet_count: 5
  droplet_size_range: [10, 50]
strobe:
  port: 24
  reply_pause_s: 0.1
flow:
  port: 26
  num_channels: 4
  pressure_range: [0, 6000]
  flow_range: [0, 1000]
EOF
```

**Note:** The Python config module (`simulation/config.py`) handles loading configuration. It will:
1. Try to load from a YAML file if you provide a path
2. Fall back to the `RIO_SIMULATION` environment variable
3. Default to `simulation=False` if neither is set

For most users, **Option A (environment variable) is recommended** as it's simpler and doesn't require managing a config file.

#### 4.2 Set Environment Variable (Recommended)

The simplest way to enable simulation is using an environment variable:

```bash
export RIO_SIMULATION=true
```

This works immediately and doesn't require any config files.

---

### Step 5: Run the Simulation

#### 5.1 Navigate to Webapp Directory

```bash
cd user-interface-software/src/webapp
```

#### 5.2 Run the Webapp

```bash
python pi_webapp.py
```

**Expected output:**
```
[SimulatedCamera] Started (640x480 @ 30 FPS)
[SimulatedSPIHandler] Initialized (bus=0, mode=2, speed=30000Hz)
[SimulatedStrobe] Initialized (port=24)
[SimulatedFlow] Initialized (port=26, channels=4)
 * Running on http://0.0.0.0:5000
```

#### 5.3 Access the Web Interface

Open your web browser and go to:

```
http://localhost:5000
```

You should see:
- Camera feed with synthetic frames (moving droplets)
- Strobe controls
- Flow controls
- ROI selection interface

---

### Step 6: Test ROI Selection

1. **Draw ROI**: Click and drag on the camera image to draw a rectangle
2. **Resize**: Drag corners or edges to resize
3. **Move**: Drag the center to move the ROI
4. **Clear**: Click "Clear ROI" button to remove

The ROI coordinates are automatically saved and can be used for droplet detection.

---

## Quick Reference Commands

### Complete Setup (One-Time)

```bash
# 1. Navigate
cd ~/Documents/GitHub/open-microfluidics-workstation

# 2. Create environment
mamba create -n rio-simulation python=3.10 -y
mamba activate rio-simulation

# 3. Install dependencies
cd user-interface-software/src
pip install Flask==1.0.2 Flask-SocketIO==4.3.2 eventlet==0.33.3 opencv-python numpy Pillow PyYAML

# 4. Enable simulation
export RIO_SIMULATION=true

# 5. Run
cd webapp
python pi_webapp.py
```

### Daily Use (After Setup)

```bash
# 1. Navigate
cd ~/Documents/GitHub/open-microfluidics-workstation

# 2. Activate environment
mamba activate rio-simulation

# 3. Enable simulation
export RIO_SIMULATION=true

# 4. Run
cd user-interface-software/src/webapp
python pi_webapp.py
```

---

## Troubleshooting Setup

### "mamba: command not found"

**Solution:** Install mamba or use conda:
```bash
# Option 1: Install mamba
conda install mamba -n base -c conda-forge

# Option 2: Use conda instead
conda create -n rio-simulation python=3.10 -y
conda activate rio-simulation
```

### "No module named 'flask'"

**Solution:** Make sure environment is activated and dependencies installed:
```bash
mamba activate rio-simulation
pip install -r requirements-simulation.txt
```

### "ImportError: cannot import name 'Container' from 'collections'"

**Solution:** This is a Python 3.10 compatibility issue with old Werkzeug. Update to newer versions:
```bash
mamba activate rio-simulation
pip install --upgrade "Werkzeug>=2.0.0" "Flask>=2.0.0" "Flask-SocketIO>=5.0.0"
# Or reinstall from requirements-simulation.txt
pip install -r requirements-simulation.txt --upgrade
```

### "No module named 'simulation'"

**Solution:** Make sure you're running from the correct directory:
```bash
# Should be in: user-interface-software/src/webapp
cd ~/Documents/GitHub/open-microfluidics-workstation/user-interface-software/src/webapp
python pi_webapp.py
```

### "Address already in use" (Port 5000)

**Solution:** Use a different port or kill the existing process:
```bash
# Option 1: Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Option 2: Run on different port (modify pi_webapp.py)
# Change: socketio.run(app, host='0.0.0.0', port=5000)
# To: socketio.run(app, host='0.0.0.0', port=5001)
```

---

## Alternative: Quick Start (If Already Set Up)

### Option 1: Environment Variable

```bash
cd ~/Documents/GitHub/open-microfluidics-workstation
mamba activate rio-simulation
export RIO_SIMULATION=true
cd user-interface-software/src/webapp
python pi_webapp.py
```

### Option 2: Configuration File

1. Ensure `rio-config.yaml` has `simulation: true`
2. Run:
```bash
cd ~/Documents/GitHub/open-microfluidics-workstation
mamba activate rio-simulation
cd user-interface-software/src/webapp
python pi_webapp.py
```

---

## What Gets Simulated

### ✅ Camera (`SimulatedCamera`)
- Generates synthetic frames at configurable FPS
- Optional droplet patterns (moving circles) for testing detection
- Supports ROI cropping
- Frame callbacks for strobe integration
- JPEG encoding for web streaming

### ✅ SPI/GPIO (`SimulatedSPIHandler`)
- Mocks Raspberry Pi SPI communication
- Mocks GPIO pin operations
- Logs all SPI transfers for debugging
- Same interface as real hardware

### ✅ Strobe (`SimulatedStrobe`)
- Mocks PIC-based strobe controller
- Maintains timing state (wait_ns, period_ns)
- Supports enable/disable, hold, trigger modes
- Simulates camera read time measurement

### ✅ Flow Controller (`SimulatedFlow`)
- Mocks 4-channel pressure/flow control
- Simulates pressure and flow values
- Supports all control modes (open-loop, closed-loop)
- PID constants storage

---

## Architecture

### Modular Design

Following the repository template pattern:

```
simulation/
├── __init__.py          # Module exports
├── config.py            # Configuration system
├── camera_simulated.py  # Simulated camera
├── spi_simulated.py     # Simulated SPI/GPIO
├── strobe_simulated.py  # Simulated strobe
└── flow_simulated.py    # Simulated flow controller
```

### Integration Points

1. **Camera Factory** (`droplet_detection/camera_base.py`)
   - `create_camera(simulation=True)` returns `SimulatedCamera`
   - Auto-detects simulation mode from environment/config

2. **SPI Handler** (can be swapped)
   - Use `SimulatedSPIHandler` instead of real `SPIHandler`
   - Same interface, no code changes needed

3. **Device Classes** (can use simulated versions)
   - `SimulatedStrobe` replaces `PiStrobe`
   - `SimulatedFlow` replaces `PiFlow`

---

## Configuration

### YAML Configuration (`rio-config.yaml`)

```yaml
simulation: true

camera:
  width: 640
  height: 480
  fps: 30
  generate_droplets: true
  droplet_count: 5
  droplet_size_range: [10, 50]

strobe:
  port: 24
  reply_pause_s: 0.1

flow:
  port: 26
  num_channels: 4
  pressure_range: [0, 6000]
  flow_range: [0, 1000]
```

### Environment Variables

```bash
export RIO_SIMULATION=true
export RIO_CONFIG_PATH=/path/to/rio-config.yaml  # Optional
```

---

## Usage Examples

### Basic Simulation

```python
from simulation import SimulatedCamera, SimulatedSPIHandler

# Create simulated camera
camera = SimulatedCamera(width=640, height=480, fps=30)
camera.start()

# Get frames
frame = camera.get_frame_array()
roi_frame = camera.get_frame_roi((100, 100, 200, 150))

# Cleanup
camera.stop()
```

### With Configuration

```python
from simulation import load_config, SimulatedCamera

config = load_config()
camera = SimulatedCamera(**config.camera)
camera.start()
```

### Integration with Existing Code

The simulation layer is designed to be a **drop-in replacement**:

```python
# Real hardware (on Raspberry Pi)
from droplet_detection import create_camera
camera = create_camera()  # Returns PiCameraV2 or PiCameraLegacy

# Simulation (on Mac/PC)
from droplet_detection import create_camera
camera = create_camera(simulation=True)  # Returns SimulatedCamera

# Both have the same interface!
camera.start()
frame = camera.get_frame_array()
camera.set_frame_callback(my_callback)
```

---

## Testing Workflow

### 1. Develop on Mac/PC (Simulation)

```bash
# Enable simulation
export RIO_SIMULATION=true

# Run webapp
cd user-interface-software/src/webapp
python pi_webapp.py

# Access at http://localhost:5000
# - Camera feed shows synthetic frames with droplets
# - All controls work (strobe, flow, etc.)
# - ROI selection works
# - Droplet detection can be tested
```

### 2. Test on Raspberry Pi (Real Hardware)

```bash
# Disable simulation
export RIO_SIMULATION=false
# or remove from config.yaml

# Run on Pi
python pi_webapp.py

# Same code, real hardware!
```

---

## Features

### Simulated Camera Features

- ✅ **Synthetic Frames**: Generates test images at configurable FPS
- ✅ **Droplet Patterns**: Moving circles simulate droplets for testing detection
- ✅ **ROI Support**: Full ROI cropping support
- ✅ **Frame Callbacks**: Compatible with strobe trigger system
- ✅ **Web Streaming**: JPEG encoding for MJPEG streams

### Simulated Hardware Features

- ✅ **State Management**: Maintains realistic device state
- ✅ **Protocol Compliance**: Follows real PIC communication protocol
- ✅ **Timing Simulation**: Simulates delays and timing
- ✅ **Debug Logging**: Logs all operations for troubleshooting

---

## Troubleshooting

### "No camera library available"

**Solution**: Enable simulation mode:
```bash
export RIO_SIMULATION=true
```

### "Simulation module not available"

**Solution**: Ensure you're in the correct directory:
```bash
cd user-interface-software/src
python -c "from simulation import SimulatedCamera"
```

### Camera not generating frames

**Solution**: Make sure to call `camera.start()`:
```python
camera = SimulatedCamera()
camera.start()  # Required!
frame = camera.get_frame_array()
```

---

## Next Steps

1. **Test ROI Selection**: Use simulated camera to test ROI selection UI
2. **Test Droplet Detection**: Use synthetic droplets to test detection algorithms
3. **Develop Features**: Build new features without hardware access
4. **Debug Issues**: Use simulation to isolate software bugs

---

## Architecture Benefits

Following the repository template patterns:

✅ **Modular**: Each device has its own simulation class  
✅ **Abstracted**: Same interface for real and simulated hardware  
✅ **Configurable**: YAML-based configuration  
✅ **Testable**: Can run full system tests without hardware  
✅ **Maintainable**: Clear separation of concerns  

---

---

## Complete Setup Example (Copy-Paste Ready)

Here's a complete example you can copy and paste into your terminal:

```bash
# ============================================
# ONE-TIME SETUP (Do this first)
# ============================================

# 1. Navigate to repository
cd ~/Documents/GitHub/open-microfluidics-workstation

# 2. Create mamba environment
mamba create -n rio-simulation python=3.10 -y

# 3. Activate environment
mamba activate rio-simulation

# 4. Install dependencies
cd user-interface-software/src
pip install -r requirements-simulation.txt

# 5. Go back to repo root
cd ~/Documents/GitHub/open-microfluidics-workstation

# 6. Enable simulation (using environment variable - recommended)
export RIO_SIMULATION=true

# ============================================
# DAILY USE (Run this each time)
# ============================================

# 1. Navigate to repository
cd ~/Documents/GitHub/open-microfluidics-workstation

# 2. Activate environment
mamba activate rio-simulation

# 3. Enable simulation mode
export RIO_SIMULATION=true

# 4. Run webapp
cd user-interface-software/src/webapp
python pi_webapp.py

# 5. Open browser to: http://localhost:5000
```

**Note:** The environment variable method (`export RIO_SIMULATION=true`) is recommended as it's simpler. If you prefer a config file, create `rio-config.yaml` in the repository root with `simulation: true`.

---

**Status**: ✅ Ready for testing  
**Branch**: `strobe-rewrite`  
**Files**: `user-interface-software/src/simulation/`

