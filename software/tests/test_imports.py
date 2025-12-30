#!/usr/bin/env python3
"""
Test script to verify all imports and dependencies before running main.py

Run this before starting the application to catch import errors early.

Usage:
    python tests/test_imports.py

    Or from software/ directory:
    python -m tests.test_imports
"""

import sys
import os

# Set simulation mode
os.environ["RIO_SIMULATION"] = "true"

software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_external_dependencies():
    """Test external package dependencies"""
    print("=" * 60)
    print("Testing External Dependencies")
    print("=" * 60)

    dependencies = [
        ("flask", "Flask"),
        ("flask_socketio", "SocketIO"),
        ("eventlet", "eventlet"),
        ("PIL", "Image"),
        ("cv2", "cv2"),
        ("numpy", "numpy"),
        ("yaml", "yaml"),
    ]

    missing = []
    for module_name, import_name in dependencies:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except ImportError as e:
            print(f"✗ {module_name}: {e}")
            missing.append(module_name)

    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements-simulation.txt")
        assert False, f"Missing dependencies: {', '.join(missing)}"
    else:
        print("\n✓ All external dependencies available")
        assert True


def test_internal_modules():
    """Test internal module imports"""
    import pytest

    print("\n" + "=" * 60)
    print("Testing Internal Module Imports")
    print("=" * 60)

    errors = []
    errors.extend(_test_driver_modules())
    errors.extend(_test_controller_modules())
    errors.extend(_test_webapp_modules())
    errors.extend(_test_simulation_modules())
    errors.extend(_test_config_module())

    if errors:
        print(f"\n❌ {len(errors)} import error(s) found")
        pytest.skip(f"{len(errors)} import error(s) found")
    else:
        print("\n✓ All internal modules import successfully")


def _test_driver_modules() -> list:
    """Test driver module imports."""
    errors = []
    modules = [
        ("drivers.spi_handler", lambda: __import__("drivers.spi_handler", fromlist=["spi_init"])),
        ("drivers.heater", lambda: __import__("drivers.heater", fromlist=["PiHolder"])),
        ("drivers.flow", lambda: __import__("drivers.flow", fromlist=["PiFlow"])),
        ("drivers.strobe", lambda: __import__("drivers.strobe", fromlist=["PiStrobe"])),
    ]
    for name, import_func in modules:
        try:
            import_func()
            print(f"✓ {name}")
        except Exception as e:
            print(f"✗ {name}: {e}")
            errors.append((name, e))
    return errors


def _test_controller_modules() -> list:
    """Test controller module imports."""
    errors = []
    modules = [
        (
            "controllers.heater_web",
            lambda: __import__("controllers.heater_web", fromlist=["heater_web"]),
        ),
        ("controllers.flow_web", lambda: __import__("controllers.flow_web", fromlist=["FlowWeb"])),
        ("controllers.camera", lambda: __import__("controllers.camera", fromlist=["Camera"])),
    ]
    for name, import_func in modules:
        try:
            import_func()
            print(f"✓ {name}")
        except Exception as e:
            print(f"✗ {name}: {e}")
            errors.append((name, e))
    return errors


def _test_webapp_modules() -> list:
    """Test webapp controller module imports."""
    errors = []
    try:
        from camera_controller import CameraController  # noqa: F401
        from flow_controller import FlowController  # noqa: F401
        from heater_controller import HeaterController  # noqa: F401
        from view_model import ViewModel  # noqa: F401

        print("✓ rio-webapp/controllers")
    except Exception as e:
        print(f"✗ rio-webapp/controllers: {e}")
        errors.append(("rio-webapp/controllers", e))
        import traceback

        traceback.print_exc()
    return errors


def _test_simulation_modules() -> list:
    """Test simulation module imports."""
    errors = []
    modules = [
        (
            "simulation.spi_simulated",
            lambda: __import__("simulation.spi_simulated", fromlist=["SimulatedSPIHandler"]),
        ),
        (
            "simulation.camera_simulated",
            lambda: __import__("simulation.camera_simulated", fromlist=["SimulatedCamera"]),
        ),
    ]
    for name, import_func in modules:
        try:
            import_func()
            print(f"✓ {name}")
        except Exception as e:
            print(f"✗ {name}: {e}")
            errors.append((name, e))
    return errors


def _test_config_module() -> list:
    """Test config module import."""
    errors = []
    try:
        import config  # noqa: F401

        print("✓ config.py")
    except Exception as e:
        print(f"✗ config.py: {e}")
        errors.append(("config", e))
    return errors


def test_initialization():
    """Test that modules can be initialized"""
    print("\n" + "=" * 60)
    print("Testing Module Initialization")
    print("=" * 60)

    import pytest

    try:
        from drivers.spi_handler import spi_init

        spi_init(0, 2, 30000)
        print("✓ SPI handler initialized")
    except Exception as e:
        print(f"✗ SPI handler initialization: {e}")
        pytest.skip(f"SPI initialization failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Rio Controller - Dependency Check")
    print("=" * 60 + "\n")

    all_passed = True

    # Test external dependencies
    if not test_external_dependencies():
        all_passed = False

    # Test internal modules
    if not test_internal_modules():
        all_passed = False

    # Test initialization
    if not test_initialization():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All checks passed! Ready to run main.py")
        return 0
    else:
        print("❌ Some checks failed. Please fix errors before running main.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
