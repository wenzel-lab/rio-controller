# Test Suite

This directory contains test scripts and utilities for the Rio microfluidics controller.

## Available Tests

### `test_imports.py`

Comprehensive dependency and import verification script. Run this before starting the application to catch import errors early.

**What it checks:**
- External package dependencies (Flask, numpy, opencv, etc.)
- Internal module imports (drivers, controllers, simulation)
- Module initialization (SPI handler setup)
- Configuration loading

### `test_drivers.py`

Unit tests for low-level hardware drivers:
- SPI handler (device selection, data transfer)
- Flow controller driver (packet handling)
- Heater driver (device communication)
- Strobe driver (timing configuration)

### `test_simulation.py`

Tests for simulation layer:
- Simulated SPI handler
- Simulated camera (frame generation, ROI capture)
- Simulated flow controller
- Simulated strobe controller
- Consistency checks (simulation vs real hardware API)

### `test_controllers.py`

Unit tests for high-level device controllers:
- Flow web controller (control modes, targets)
- Heater web controller (temperature reading)
- Camera controller (data structures)
- Configuration import

### `test_integration.py`

Integration tests for component interaction:
- Hardware initialization sequence
- Camera-strobe integration
- Simulation mode end-to-end
- Error handling scenarios

### `test_droplet_detection.py`

Unit tests for droplet detection pipeline:
- Preprocessing (background subtraction, thresholding)
- Segmentation (contour detection, filtering)
- Measurement (geometric metrics calculation)
- Artifact rejection (temporal filtering)
- Detector pipeline integration
- Histogram and statistics

### `test_measurement_methods.py`

Tests for droplet measurement algorithms:
- Centroid calculation
- Ellipse fitting
- Equivalent diameter formulas
- Radius offset correction
- Multiple contours handling

### `test_all.py`

Run all tests in the suite. Discovers and runs all test modules.

## Running Tests

All tests should be run from the `software/` directory with the mamba environment activated:

```bash
mamba activate rio-simulation
cd software

# Recommended: Use pytest (installed in rio-simulation environment)
pytest -v

# Run specific test suite
pytest tests/test_imports.py
pytest tests/test_drivers.py
pytest tests/test_simulation.py
pytest tests/test_controllers.py
pytest tests/test_integration.py
pytest tests/test_droplet_detection.py
pytest tests/test_measurement_methods.py

# Run all tests
pytest -v

# Or using Python unittest directly
python tests/test_all.py
python -m tests.test_all
```

## Test tiers and boundaries (what each set exercises)

This suite is most useful when read “bottom-up”:

- **Tier 1 (routine, simulation by default)**: fast CI/AI-friendly, uses `RIO_SIMULATION=true`. Covers imports, drivers (simulated), controllers, web layer smoke, and droplet detection algorithms.
- **Tier 2 (integration + optional datasets)**: still simulation, but may need optional data (e.g., droplet images). If absent, tests must skip with a clear reason.
- **Tier 3 (hardware/Pi-only)**: opt-in, marked tests that should not run by default. Run manually on hardware when needed.

Logical stacking:
- **Imports + environment sanity**: `test_imports.py`
- **Drivers layer** (`software/drivers/`): SPI packet framing and driver APIs
- **Simulation layer** (`software/simulation/`): drop-in “no hardware” replacements
- **Controllers layer** (`software/controllers/`): orchestration/state; should be runnable in simulation mode
- **Web layer** (`software/rio-webapp/`): mostly exercised indirectly via controller tests and route wiring
- **Droplet detection** (`software/droplet-detection/`): pure algorithm tests + some integration coverage

## Pytest configuration and markers

`software/pyproject.toml` defines pytest defaults for this repo (test discovery under `tests/`, `test_*.py`, etc.) and declares these markers:

- `simulation`: tests that require `RIO_SIMULATION=true`
- `integration`: cross-component tests (often slower / more stateful)
- `slow`: opt-in slow tests

Examples:

```bash
cd software
export RIO_SIMULATION=true

# Skip slow tests
pytest -m "not slow" -v

# Only integration tests
pytest -m "integration" -v
```

## Dataset-dependent droplet tests (optional)

Some droplet-detection tests and tools can optionally look for a `droplet_AInalysis` checkout (see `software/droplet-detection/test_data_loader.py`). If you don’t have that dataset locally, those tests/utilities may skip or need configuration.

For droplet benchmarking/optimization workflows, see `droplet-detection-testing_and_optimization_guide.md`.

**Optional droplet image dataset (for simulation/tests)**
- Provide via `RIO_DROPLET_TESTDATA_DIR` (preferred) or place under `software/tests/data/droplet/`.
- If absent, simulation will fall back to synthetic images and any dataset-dependent tests should skip with a clear reason.

## Test Output

- ✓ indicates successful test
- ✗ indicates failed test
- All tests should pass before deploying or refactoring

## Test Coverage

These tests help ensure:
1. **Code correctness**: Individual modules work as expected
2. **Integration**: Components work together correctly
3. **Simulation fidelity**: Simulation matches real hardware behavior
4. **Error handling**: Graceful handling of edge cases
5. **Refactoring safety**: Tests catch regressions during code changes

## Code Quality Standards

The codebase follows these quality standards:
- **Type hints**: Use type annotations where appropriate
- **Docstrings**: All public classes and methods should have docstrings
- **Formatting**: Code formatted with `black` (line-length=100)
- **Linting**: `flake8` with max-line-length=100
- **Type checking**: `mypy` for static type analysis (dynamic imports excluded)
- **Testing**: Comprehensive test coverage for all modules

Run code quality checks:
```bash
# Format code
black .

# Type checking
mypy . --exclude droplet-detection

# Linting
flake8 controllers/ rio-webapp/ main.py tests/ --max-line-length=100
```

## Adding New Tests

When adding new test files:
1. Place them in this `tests/` directory
2. Follow naming convention: `test_*.py`
3. Use unittest framework for consistency (or pytest)
4. Set `RIO_SIMULATION=true` for all tests if hardware access is not required
5. Update this README with a description
6. Ensure tests can be run independently or as a module
7. Add docstrings to test classes and methods for clarity

