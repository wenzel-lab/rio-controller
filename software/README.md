# Rio Microfluidics Controller - Software

This directory contains all software for the Rio microfluidics controller system.

> **Package Compatibility**: See `docs/PACKAGE_COMPATIBILITY.md` for detailed compatibility information across Raspberry Pi 32/64-bit and Mac/PC/Ubuntu platforms.

## Folder Structure

```
software/
├── main.py                 # Application entry point
├── config.py               # Configuration constants (system-wide)
├── rio-webapp/             # Web application components
│   ├── controllers/       # Web controllers (HTTP/WebSocket handlers)
│   │   ├── camera_controller.py
│   │   ├── flow_controller.py
│   │   ├── heater_controller.py
│   │   └── view_model.py
│   ├── routes.py         # Flask route definitions
│   ├── templates/         # HTML templates
│   │   ├── index.html
│   │   ├── camera_pi.html
│   │   └── camera_none.html
│   └── static/            # JavaScript, CSS
│       └── roi_selector.js
│
├── drivers/                # Low-level device drivers
│   ├── spi_handler.py     # SPI and GPIO communication
│   ├── flow.py            # Low-level flow controller driver
│   ├── heater.py          # Low-level heater driver
│   ├── strobe.py          # Low-level strobe driver
│   └── camera/            # Camera abstraction layer
│       ├── camera_base.py
│       ├── pi_camera_legacy.py
│       └── pi_camera_v2.py
│
├── controllers/            # Device controllers (business logic layer)
│   ├── flow_web.py        # Flow control device controller
│   ├── heater_web.py      # Heater control device controller
│   ├── camera.py          # Camera device controller
│   ├── strobe_cam.py      # Strobe-camera integration controller
│   └── droplet_detector_controller.py  # Droplet detection controller
│
│   Note: In hardware control systems, "controller" refers to device
│   control logic (equivalent to "Model" in MVC). See docs/ARCHITECTURE_TERMINOLOGY.md
│
├── simulation/             # Simulation layer (for testing without hardware)
│   ├── camera_simulated.py
│   ├── flow_simulated.py
│   ├── strobe_simulated.py
│   └── spi_simulated.py
│
├── tests/                  # Test suite
│   ├── test_imports.py     # Dependency verification
│   ├── test_drivers.py     # Driver unit tests
│   ├── test_simulation.py  # Simulation layer tests
│   ├── test_controllers.py # Controller unit tests
│   ├── test_integration.py # Integration tests
│   └── test_all.py         # Run all tests
│
└── droplet-detection/      # Droplet detection algorithms
    ├── detector.py         # Main detection pipeline
    ├── preprocessor.py     # Image preprocessing
    ├── segmenter.py        # Contour detection
    ├── measurer.py         # Geometric measurements
    ├── artifact_rejector.py # Temporal filtering
    ├── histogram.py        # Statistics and histograms
    ├── config.py           # Configuration management
    ├── benchmark.py        # Performance benchmarking
    ├── optimize.py         # Parameter optimization
    └── test_integration.py  # Integration tests
```

## Launching the Software

### Prerequisites

1. **Python Environment**: Python 3.8+ recommended
   - **Recommended**: Use mamba/conda environment (see below)
   - **Never install to system Python root** - always use a virtual environment

2. **Setup with Mamba/Conda** (Recommended):
   ```bash
   # Create and activate environment
   mamba create -n rio-controller python=3.10 -y
   mamba activate rio-controller
   
   # Install dependencies based on your platform:
   cd software
   
   # For Raspberry Pi 32-bit:
   pip install -r requirements_32bit.txt
   
   # For Raspberry Pi 64-bit:
   pip install -r requirements_64bit.txt
   
   # For simulation (Mac/PC/Ubuntu):
   pip install -r requirements-simulation.txt
   ```

3. **Hardware vs Simulation**:
   - **Real Hardware**: Requires Raspberry Pi with SPI/GPIO access
   - **Simulation Mode**: Set environment variable `RIO_SIMULATION=true` to run without hardware

### Running the Web Application

1. **Navigate to the software directory**:
   ```bash
   cd software
   ```

2. **Run the application**:
   ```bash
   # Default port (5000)
   python main.py
   
   # Custom port
   python main.py 5001
   
   # Using environment variable
   export RIO_PORT=5001
   python main.py
   ```

3. **Access the web interface**:
   - Open your browser to `http://localhost:5000` (or your specified port)
   - The interface provides tabs for:
     - **Camera View**: Live camera feed with ROI selection and strobe control
     - **Camera Config**: Camera selection and debug information
     - **Flow Control**: Pressure and flow control for 4 channels
     - **Heaters**: Temperature and stirring control for 4 heaters
     - **Droplet Detection**: Real-time droplet detection with histogram visualization

### Simulation Mode

To run without hardware (for testing on a Mac/PC):

**Option 1: Quick setup and run**
```bash
cd software
./setup-simulation.sh    # First time setup
./run-simulation.sh      # Run simulation
```

**Option 2: Manual setup**
```bash
cd software
export RIO_SIMULATION=true
python main.py
```

The `setup-simulation.sh` script sets up the mamba environment and installs dependencies. The `run-simulation.sh` script activates the environment and runs the application in simulation mode.

Configuration can be set in `rio-config.yaml` (in the `software/` directory) or via the `RIO_SIMULATION` environment variable.

This enables simulated SPI, GPIO, camera, and device controllers, allowing you to test the web interface and logic without physical hardware.

### Pre-Flight Check

Before running the application, verify all dependencies are installed:

```bash
# In your mamba environment
mamba activate rio-simulation
cd software
python tests/test_imports.py
```

This will check all external and internal dependencies. All checks should pass (✓) before running `main.py`.

### Running Tests

The test suite includes unit tests, integration tests, and simulation tests:

```bash
# Run all tests (recommended: use pytest from mamba environment)
cd software
pytest -v

# Run specific test suites
pytest tests/test_drivers.py      # Low-level driver tests
pytest tests/test_simulation.py   # Simulation layer tests
pytest tests/test_controllers.py  # Controller tests
pytest tests/test_integration.py  # Integration tests
pytest tests/test_droplet_detection.py  # Droplet detection tests
```

**Code Quality Checks:**
```bash
# Format code (black)
black .

# Type checking (mypy)
mypy . --exclude droplet-detection

# Linting (flake8)
flake8 controllers/ rio-webapp/ main.py tests/ --max-line-length=100
```

See `tests/README.md` for detailed test documentation.

### Droplet Detection

The system includes real-time droplet detection capabilities with a modular pipeline architecture:

**Quick Start:**
1. Set ROI in Camera View tab
2. Go to Droplet Detection tab
3. Click "Start Detection"
4. View real-time histograms and statistics

**Features:**
- Real-time processing with configurable frame rate
- Background subtraction for static artifact removal
- Contour-based segmentation with filtering
- Geometric measurements (area, diameter, aspect ratio)
- Temporal artifact rejection
- Sliding-window histogram with configurable bins
- Performance monitoring and timing instrumentation

**Documentation:**
- User Guide: `docs/droplet_detection_user_guide.md`
- Developer Guide: `docs/droplet_detection_developer_guide.md`
- Testing & Optimization: `docs/testing_and_optimization_guide.md`

**Testing:**
```bash
# Run all tests (includes droplet detection tests)
cd software
pytest -v

# Run integration tests
python -m droplet_detection.test_integration

# Run performance benchmarks
python -m droplet_detection.benchmark

# Optimize parameters
python -m droplet_detection.optimize
```

**API:**
- REST API: `GET /api/droplet/status`, `POST /api/droplet/start`, etc.
- WebSocket: `socket.emit('droplet', {cmd: 'start'})`

### Troubleshooting

**Port already in use**:
```bash
# Find and kill process using the port
lsof -ti:5000 | xargs kill -9

# Or use a different port
python main.py 5001
```

**Import errors**:
- Ensure you're running from `software/` directory
- **Ensure mamba environment is activated**: `mamba activate rio-controller`
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using the environment Python: `which python` should show your mamba environment path

**Hardware not detected**:
- Enable simulation mode: `export RIO_SIMULATION=true`
- Or ensure you're running on a Raspberry Pi with proper SPI/GPIO permissions

## Development

### Adding New Features

- **New device controller**: Add to `controllers/`
- **New hardware driver**: Add to `drivers/`
- **New web route**: Add to `main.py` or create new controller in `rio-webapp/controllers/`
- **New simulation**: Add to `simulation/` following existing patterns

### Code Organization Principles

1. **Separation of Concerns**: 
   - Drivers: Hardware communication
   - Device Controllers: Business logic (equivalent to MVC "Model")
   - Web Controllers: HTTP/WebSocket handling (MVC "Controller")
   - Views: Templates and static files (MVC "View")
2. **MVC+S Architecture**: Model-View-Controller-Simulation layers
3. **Simulation Support**: All hardware interactions have simulation equivalents
4. **Configuration**: Centralize constants in `config.py` (system-wide)

See `docs/ARCHITECTURE_TERMINOLOGY.md` for detailed explanation of terminology.

