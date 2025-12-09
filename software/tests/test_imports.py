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
os.environ['RIO_SIMULATION'] = 'true'

# Add parent directory (software/) to path so we can import modules
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if software_dir not in sys.path:
    sys.path.insert(0, software_dir)

def test_external_dependencies():
    """Test external package dependencies"""
    print("=" * 60)
    print("Testing External Dependencies")
    print("=" * 60)
    
    dependencies = [
        ('flask', 'Flask'),
        ('flask_socketio', 'SocketIO'),
        ('eventlet', 'eventlet'),
        ('PIL', 'Image'),
        ('cv2', 'cv2'),
        ('numpy', 'numpy'),
        ('yaml', 'yaml'),
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
        return False
    else:
        print("\n✓ All external dependencies available")
        return True

def test_internal_modules():
    """Test internal module imports"""
    print("\n" + "=" * 60)
    print("Testing Internal Module Imports")
    print("=" * 60)
    
    errors = []
    
    # Test drivers
    try:
        from drivers.spi_handler import spi_init, PORT_HEATER1, PORT_HEATER2, PORT_HEATER3, PORT_HEATER4, PORT_FLOW
        print("✓ drivers.spi_handler")
    except Exception as e:
        print(f"✗ drivers.spi_handler: {e}")
        errors.append(('drivers.spi_handler', e))
    
    try:
        from drivers.heater import PiHolder
        print("✓ drivers.heater")
    except Exception as e:
        print(f"✗ drivers.heater: {e}")
        errors.append(('drivers.heater', e))
    
    try:
        from drivers.flow import PiFlow
        print("✓ drivers.flow")
    except Exception as e:
        print(f"✗ drivers.flow: {e}")
        errors.append(('drivers.flow', e))
    
    try:
        from drivers.strobe import PiStrobe
        print("✓ drivers.strobe")
    except Exception as e:
        print(f"✗ drivers.strobe: {e}")
        errors.append(('drivers.strobe', e))
    
    # Test controllers
    try:
        from controllers.heater_web import heater_web
        print("✓ controllers.heater_web")
    except Exception as e:
        print(f"✗ controllers.heater_web: {e}")
        errors.append(('controllers.heater_web', e))
    
    try:
        from controllers.flow_web import FlowWeb
        print("✓ controllers.flow_web")
    except Exception as e:
        print(f"✗ controllers.flow_web: {e}")
        errors.append(('controllers.flow_web', e))
    
    try:
        from controllers.camera import Camera
        print("✓ controllers.camera")
    except Exception as e:
        print(f"✗ controllers.camera: {e}")
        errors.append(('controllers.camera', e))
    
    # Test webapp controllers
    try:
        # rio-webapp/controllers is relative to software/ directory
        rio_webapp_controllers_dir = os.path.join(software_dir, 'rio-webapp', 'controllers')
        if rio_webapp_controllers_dir not in sys.path:
            sys.path.insert(0, rio_webapp_controllers_dir)
        from camera_controller import CameraController
        from flow_controller import FlowController
        from heater_controller import HeaterController
        from view_model import ViewModel
        print("✓ rio-webapp/controllers")
    except Exception as e:
        print(f"✗ rio-webapp/controllers: {e}")
        errors.append(('rio-webapp/controllers', e))
        import traceback
        traceback.print_exc()
    
    # Test simulation
    try:
        from simulation.spi_simulated import SimulatedSPIHandler, SimulatedGPIO
        print("✓ simulation.spi_simulated")
    except Exception as e:
        print(f"✗ simulation.spi_simulated: {e}")
        errors.append(('simulation.spi_simulated', e))
    
    try:
        from simulation.camera_simulated import SimulatedCamera
        print("✓ simulation.camera_simulated")
    except Exception as e:
        print(f"✗ simulation.camera_simulated: {e}")
        errors.append(('simulation.camera_simulated', e))
    
    # Test config
    try:
        import config
        print("✓ config.py")
    except Exception as e:
        print(f"✗ config.py: {e}")
        errors.append(('config', e))
    
    if errors:
        print(f"\n❌ {len(errors)} import error(s) found")
        return False
    else:
        print("\n✓ All internal modules import successfully")
        return True

def test_initialization():
    """Test that modules can be initialized"""
    print("\n" + "=" * 60)
    print("Testing Module Initialization")
    print("=" * 60)
    
    try:
        from drivers.spi_handler import spi_init
        spi_init(0, 2, 30000)
        print("✓ SPI handler initialized")
    except Exception as e:
        print(f"✗ SPI handler initialization: {e}")
        return False
    
    return True

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

if __name__ == '__main__':
    sys.exit(main())

