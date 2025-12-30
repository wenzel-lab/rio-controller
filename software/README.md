# Rio Microfluidics Controller - Software

This directory contains all software for the Rio microfluidics controller system.

**Platform compatibility (summary):**
- **Developer machines (Mac/PC/Linux)**: run in **simulation** (`RIO_SIMULATION=true`) using `requirements-simulation.txt`.
- **Raspberry Pi 32-bit**: hardware mode with Pi-specific packages (see `requirements_32bit.txt` or use the deployment bundle).
- **Raspberry Pi 64-bit**: hardware mode with Pi-specific packages (see `requirements_64bit.txt`).

## Structure overview (start here)

Use these short READMEs to navigate the codebase. Detailed implementation lives in the code; this page stays intentionally shallow.

- Core architecture: `../ARCHITECTURE.md`
- Device controllers (business logic): [`controllers/README.md`](controllers/README.md)
- Drivers (hardware adapters): [`drivers/README.md`](drivers/README.md)
  - Camera abstraction/backends: [`drivers/camera/README.md`](drivers/camera/README.md)
- Web app (Flask + UI): [`rio-webapp/README.md`](rio-webapp/README.md)
  - Web controllers (WS/HTTP handlers): [`rio-webapp/controllers/README.md`](rio-webapp/controllers/README.md)
- Droplet detection pipeline: [`droplet-detection/README.md`](droplet-detection/README.md)
- Simulation layer: [`simulation/README.md`](simulation/README.md)
- Tests: [`tests/README.md`](tests/README.md)
- Configuration examples: [`configurations/README.md`](configurations/README.md)

## Runtime wiring (how the software fits together)

The main runtime entry point is **`software/main.py`**, which wires the layers together in a fairly direct way:

- **SPI/GPIO backend selection** happens inside `drivers/spi_handler.py` (simulation vs hardware is chosen via `RIO_SIMULATION=true|false`).
- **Device controllers** are created in `main.py`:
  - `controllers/flow_web.py` (`FlowWeb`) wraps `drivers/flow.py` (`PiFlow`)
  - `controllers/heater_web.py` (`heater_web`) wraps `drivers/heater.py` (`PiHolder`)
  - `controllers/camera.py` (`Camera`) composes `controllers/strobe_cam.py` (`PiStrobeCam`)
    - `PiStrobeCam` composes `drivers/strobe.py` (`PiStrobe`) + `drivers/camera/` (`BaseCamera` backends)
  - Optional droplet detection: `controllers/droplet_detector_controller.py` bridges camera ROI frames into `droplet-detection/`
- **Web layer** is created next:
  - Socket.IO handlers live in `rio-webapp/controllers/` and call into the device controllers above.
  - HTTP routes (and some `/api/droplet/*` endpoints) are registered via `rio-webapp/routes.py`.

If you’re auditing logic, reading order that matches the runtime is:
`main.py` → `rio-webapp/routes.py` + `rio-webapp/controllers/*` → `controllers/*` → `drivers/*` → firmware projects under `../hardware-modules/*/*_pic/`.

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

The `setup-simulation.sh` script creates a conda/mamba environment named **`rio-simulation`** and installs dependencies. The `run-simulation.sh` script activates that environment and runs the app in simulation mode.

Note: `setup-simulation.sh` also creates a `rio-config.yaml` file for simulation settings, but **the main app currently selects simulation via `RIO_SIMULATION=true`**; `rio-config.yaml` is not a primary runtime configuration source for `main.py`.

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
- Implementation: `droplet-detection/` (module docstrings + code)
- Tests & optimization: `tests/droplet-detection-testing_and_optimization_guide.md`

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
- **Ensure your conda/mamba environment is activated** (e.g., `mamba activate rio-simulation` for simulation, or whatever env you created for hardware/dev)
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

Terminology reminder: “device controllers” live in `controllers/`, while “web controllers” live in `rio-webapp/controllers/`.

