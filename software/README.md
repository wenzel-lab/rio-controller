# Rio Microfluidics Controller - Software

This directory contains all software for the Rio microfluidics controller system.

**Platform compatibility (summary):**
- **Developer machines (Mac/PC/Linux)**: run in **simulation** (`RIO_SIMULATION=true`) using `requirements-simulation.txt`.
- **Raspberry Pi (32-bit)**: hardware mode with Pi-specific packages (see `requirements-pi.txt` or use the deployment bundle).

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
- API interface: [`api/README.md`](api/README.md)
- API client library: [`api/client/README.md`](api/client/README.md)

### Runtime wiring (how the software fits together)

The main runtime entry point is **`software/main.py`**, which wires the layers together in a fairly direct way:

- **SPI/GPIO backend selection** happens inside `drivers/spi_handler.py` (simulation vs hardware defaults to `RIO_SIMULATION=true|false`, but `runtime.default_backend` in `rio-config.yaml` can set this when `RIO_SIMULATION` is not explicitly set).
- **Device controllers** are created in `main.py`:
  - `controllers/flow_web.py` (`FlowWeb`) wraps `drivers/flow.py` (`PiFlow`)
  - `controllers/heater_web.py` (`heater_web`) wraps `drivers/heater.py` (`PiHolder`)
  - `controllers/camera.py` (`Camera`) composes `controllers/strobe_cam.py` (`PiStrobeCam`)
    - `PiStrobeCam` composes `drivers/strobe.py` (`PiStrobe`) + `drivers/camera/` (`BaseCamera` backends)
  - Optional droplet detection: `controllers/droplet_detector_controller.py` bridges camera ROI frames into `droplet-detection/`
- **Web layer** is created next:
  - Socket.IO handlers live in `rio-webapp/controllers/` and call into the device controllers above.
  - HTTP routes (and some `/api/droplet/*` endpoints) are registered via `rio-webapp/routes.py`.

- You should not need to touch `PYTHONPATH` or add `sys.path` in modules Runtime: `python main.py` calls `path_bootstrap.bootstrap_runtime()` for you.

If you're auditing logic, reading order that matches the runtime is:
`main.py` → `rio-webapp/routes.py` + `rio-webapp/controllers/*` → `controllers/*` → `drivers/*` → firmware projects under `../hardware-modules/*/*_pic/`.

## Requirements Files

The repository includes **3 requirements files** for different deployment scenarios:

1. **`requirements-simulation.txt`** — Development/simulation (Mac/PC/Ubuntu)
   - For running the application without hardware
   - Includes testing tools (pytest, black, mypy, etc.)
   - Use with mamba/conda virtual environment

2. **`requirements-pi.txt`** — Raspberry Pi deployment (32-bit)
   - Supports legacy Pi camera (`picamera`)
   - Excludes hardware packages (install via apt: `python3-spidev`, `python3-rpi.gpio`, `python3-picamera`)
   - Excludes OpenCV (install via apt: `python3-opencv` for fast pre-built version)
   - Uses `numpy<2.0.0` for 32-bit compatibility (numpy 2.0+ doesn't work on 32-bit)
   - Used by deployment bundle generation

3. **`requirements-api.txt`** — API server dependencies (additive)
   - Additional packages for the FastAPI-based network API
   - Install after base requirements: `pip install -r requirements-api.txt`
   - Used when running the API server (`software/api/main.py`)

**Note**: Hardware packages (spidev, RPi.GPIO, picamera) and OpenCV should be installed via `apt` on Raspberry Pi for faster installation and better compatibility. The requirements file documents this in comments.

## Setup and Deployment

**IMPORTANT:** Choose the correct setup based on your platform:

- **Mac/PC/Ubuntu (Development)**: See [Development Setup (Mac/PC/Ubuntu)](#development-setup-macpcubuntu) below
  - Uses mamba/conda virtual environments
  - For simulation and development
  - **NOT for Raspberry Pi deployment**

- **Raspberry Pi (Production)**: See [Raspberry Pi Deployment](#raspberry-pi-deployment) below
  - Uses system Python (no virtual environment)
  - For actual hardware operation
  - `pi-deployment/` is generated from `software/` using `scripts/deploy/create-pi-deployment.sh`

### Choose Your Scenario

- **Scenario 1 — Pi image (UI on Pi, optional API)**: Flask UI autostarts on the Pi, API is optional.
- **Scenario 2 — Pi API-only + external UI/camera**: Pi exposes API for Pi-HAT modules; external computer runs UI + image processing.
- **Scenario 2b — Pi API-only + Pi camera via API**: legacy `picamera` remains on the Pi; clients control via API.

---

## Development Setup (Mac/PC/Ubuntu)

**This section is for development on Mac/PC/Ubuntu only. For Raspberry Pi deployment, skip to the [Raspberry Pi Deployment](#raspberry-pi-deployment) section.**

### Prerequisites

1. **Python Environment**: Python 3.8+ recommended
   - **Required**: Use mamba/conda environment (see below)
   - **Never install to system Python root** - always use a virtual environment for development

2. **Setup with Mamba/Conda** (Required for Development):
   ```bash
   # Create and activate environment
   mamba create -n rio-simulation python=3.10 -y
   mamba activate rio-simulation
   
   # Install dependencies for simulation mode (Mac/PC/Ubuntu):
   cd software
   pip install -r requirements-simulation.txt
   ```

3. **Hardware vs Simulation**:
   - **Development/Simulation**: Set environment variable `RIO_SIMULATION=true` to run without hardware
   - **Real Hardware**: Requires Raspberry Pi deployment (see [Raspberry Pi Deployment](#raspberry-pi-deployment) below)

### Running the Development Application (Simulation Mode)

**Note:** This runs in simulation mode on Mac/PC. For actual hardware, see [Raspberry Pi Deployment](#raspberry-pi-deployment).

1. **Navigate to the software directory**:
   ```bash
   cd software
   ```

2. **Run the application in simulation mode**:
   ```bash
   # Default port (5000)
   # set RIO_SIMULATION=true (Windows)
   export RIO_SIMULATION=true
   python main.py
   
   # Custom port
   export RIO_SIMULATION=true
   python main.py 5001
   
   # Using environment variable
   export RIO_SIMULATION=true
   export RIO_PORT=5001
   python main.py
   ```
   ROI modes: default is software ROI; set `RIO_ROI_MODE=hardware` to request hardware ROI when the active camera backend supports it (falls back to software if not).
   Hybrid UI: set `RIO_REMOTE_MODULES=flow,heater,pump,camera` and `RIO_REMOTE_API_URL=http://raspberrypi.local:8000` to use API-backed modules.

3. **Access the web interface**:
   - Open your browser to `http://localhost:5000` (or your specified port)
   - The interface provides tabs for:
     - **Camera View**: Live camera feed with ROI selection and strobe control
     - **Camera Config**: Camera selection and debug information
     - **Flow Control**: Pressure and flow control for 4 channels
     - **Heaters**: Temperature and stirring control for 4 heaters
     - **Droplet Detection**: Real-time droplet detection with histogram visualization

### Simulation Mode (Quick Start)

To run without hardware (for testing on a Mac/PC):

**Option 1: Quick setup and run**
```bash

# NOTE: These scripts are written for conda/mamba environments. If you are using virtualenv, you will need to modify the scripts. 

# on Linux/Mac
./scripts/dev/setup-simulation.sh    # First time setup
./scripts/dev/run-simulation.sh      # Run simulation

# on Windows (Git Bash)
bash ./scripts/dev/setup-simulation.sh 
bash ./scripts/dev/run-simulation.sh 

```

Need custom parameters for simulation (frame size, ROI defaults, feature flags)? See `configurations/README.md` for the environment-variable profiles and examples you can export before running. Mixed backend selection (e.g., syringe pump hardware while other modules are simulated) is configured via the `runtime` block in `rio-config.yaml` or with `RIO_MODULE_BACKENDS`.

**Option 2: Manual setup**
```bash
cd software
# set RIO_SIMULATION=true (Windows)
export RIO_SIMULATION=true
python main.py
```

The `scripts/dev/setup-simulation.sh` script creates a conda/mamba environment named **`rio-simulation`** and installs dependencies. The `scripts/dev/run-simulation.sh` script activates that environment and runs the app in simulation mode.

Note: `setup-simulation.sh` also creates a `rio-config.yaml` file for simulation settings. `software/main.py` now reads the `runtime` section from `rio-config.yaml` (or `RIO_CONFIG_FILE`) to choose the default backend and per-module overrides (currently used for the syringe pump).

This enables simulated SPI, GPIO, camera, and device controllers, allowing you to test the web interface and logic without physical hardware.

---

## API server

The network API (FastAPI/LabThings) lives under `software/api/`. It is an interface
layer only; device controllers and drivers remain unchanged.

- Install API extras (from `software/`):

```bash
pip install -r requirements-api.txt
```

- Run (simulation example):

```bash
export RIO_SIMULATION=true
python -m api.main  # default port 8000
```

- Endpoints available in the skeleton:
  - `GET /api/system/health`
  - `GET /api/system/capabilities`
  - See `api/README.md` for complete endpoint documentation
  - See `api/client/README.md` for Python client library and Jupyter notebooks

Later steps will expose full control/streaming surfaces.

---

## Raspberry Pi Deployment

**This section is for deploying to actual Raspberry Pi hardware. For Mac/PC development, see [Development Setup (Mac/PC/Ubuntu)](#development-setup-macpcubuntu) above.**

**IMPORTANT:** 
- **DO NOT use mamba/conda on Raspberry Pi** - use system Python
- **DO NOT create virtual environments on Pi** - install to system Python
- `pi-deployment/` is a generated bundle; it is the runtime copy used on the Pi

### Creating the Pi Deployment Bundle (from Mac/PC)

**On your Mac/PC (not on the Pi):** Generate the deployment bundle and copy it to your Raspberry Pi:

**Linux/Mac:**
```bash
cd /path/to/rio-controller
./scripts/deploy/create-pi-deployment.sh
rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' \
  pi-deployment/ pi@raspberrypi.local:~/rio-controller/
```

**Windows:**
```cmd
cd C:\path\to\rio-controller
create-pi-deployment.bat
# Then use your preferred method to copy pi-deployment/ to the Pi (e.g., WinSCP, SCP)
```

After syncing, **SSH to your Pi**:
- Run `./setup.sh` (first time only - installs packages to system Python)
- Run `./run.sh` or `python main.py` (to start the application)

### Pi Mode Switching (UI vs API)

To switch between UI-only and API-only services on the Pi:
```bash
./scripts/pi/rio-mode ui
./scripts/pi/rio-mode api
./scripts/pi/rio-mode status
```
Install the systemd units first:
```bash
sudo cp ./scripts/pi/systemd/rio-ui.service /etc/systemd/system/
sudo cp ./scripts/pi/systemd/rio-api.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Key Differences: Development vs Production

| Aspect | Mac/PC Development | Raspberry Pi Production |
|--------|-------------------|------------------------|
| Python Environment | mamba/conda virtual environment | System Python (no venv) |
| Installation | `pip install -r requirements-simulation.txt` | `python3 -m pip install --user -r requirements-pi.txt` |
| Hardware | Simulated | Real hardware |
| Mode | `RIO_SIMULATION=true` | `RIO_SIMULATION=false` |
| Dependencies | See `requirements-simulation.txt` | See `pi-deployment/requirements-pi.txt` |

### Pre-Flight Check (Development Only)

Before running the application in development mode, verify all dependencies are installed:

```bash
# Activate your mamba environment
mamba activate rio-simulation
cd software
python tests/test_imports.py
```

This will check all external and internal dependencies. All checks should pass (✓) before running `main.py`.

**Note:** For Raspberry Pi deployment, the setup script (`pi-deployment/setup.sh`) handles dependency verification automatically.

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

**CI:** The GitHub Actions workflow (`.github/workflows/ci.yml`) runs `black`, `flake8`, `mypy`, and `pytest` in simulation mode on push/PRs.

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
- Check that all dependencies are installed: `pip install -r requirements-simulation.txt`
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

