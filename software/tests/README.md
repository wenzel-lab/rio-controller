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

### `test_all.py`

Run all tests in the suite. Discovers and runs all test modules.

## Running Tests

All tests should be run from the `software/` directory with the mamba environment activated:

```bash
mamba activate rio-simulation
cd software

# Run specific test suite
python tests/test_imports.py
python tests/test_drivers.py
python tests/test_simulation.py
python tests/test_controllers.py
python tests/test_integration.py

# Run all tests
python tests/test_all.py

# Or as modules
python -m tests.test_imports
python -m tests.test_all
```

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

## Adding New Tests

When adding new test files:
1. Place them in this `tests/` directory
2. Follow naming convention: `test_*.py`
3. Use unittest framework for consistency
4. Set `RIO_SIMULATION=true` for all tests
5. Update this README with a description
6. Ensure tests can be run independently or as a module

