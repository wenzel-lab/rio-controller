"""
Test script for camera abstraction layer

Usage:
    python test_camera.py

Tests:
    - Camera creation (auto-detect)
    - Frame capture
    - ROI capture
    - Configuration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from droplet_detection import create_camera, BaseCamera
import numpy as np


def test_camera_creation():
    """Test camera factory function"""
    print("Testing camera creation...")
    try:
        camera = create_camera()
        print(f"✓ Camera created: {type(camera).__name__}")
        return camera
    except Exception as e:
        print(f"✗ Camera creation failed: {e}")
        return None


def test_camera_start_stop(camera: BaseCamera):
    """Test camera start/stop"""
    print("\nTesting camera start/stop...")
    try:
        camera.start()
        print("✓ Camera started")
        camera.stop()
        print("✓ Camera stopped")
        return True
    except Exception as e:
        print(f"✗ Start/stop failed: {e}")
        return False


def test_frame_capture(camera: BaseCamera):
    """Test single frame capture"""
    print("\nTesting frame capture...")
    try:
        camera.start()
        frame = camera.get_frame_array()
        print(f"✓ Frame captured: shape={frame.shape}, dtype={frame.dtype}")
        camera.stop()
        return True
    except Exception as e:
        print(f"✗ Frame capture failed: {e}")
        return False


def test_roi_capture(camera: BaseCamera):
    """Test ROI capture"""
    print("\nTesting ROI capture...")
    try:
        camera.start()
        # Test ROI: (x, y, width, height) = (100, 100, 200, 150)
        roi = (100, 100, 200, 150)
        roi_frame = camera.get_frame_roi(roi)
        print(f"✓ ROI captured: shape={roi_frame.shape}, expected=(150, 200, 3)")
        camera.stop()
        return True
    except Exception as e:
        print(f"✗ ROI capture failed: {e}")
        return False


def test_configuration(camera: BaseCamera):
    """Test camera configuration"""
    print("\nTesting configuration...")
    try:
        config = {
            "Width": 640,
            "Height": 480,
            "FrameRate": 30
        }
        camera.set_config(config)
        print("✓ Configuration set")
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("Camera Abstraction Layer Test")
    print("=" * 50)
    
    # Test camera creation
    camera = test_camera_creation()
    if camera is None:
        print("\n✗ Cannot continue without camera")
        return
    
    # Run tests
    tests = [
        ("Start/Stop", lambda: test_camera_start_stop(camera)),
        ("Frame Capture", lambda: test_frame_capture(camera)),
        ("ROI Capture", lambda: test_roi_capture(camera)),
        ("Configuration", lambda: test_configuration(camera)),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    # Cleanup
    try:
        camera.close()
    except:
        pass
    
    # Exit code
    all_passed = all(result for _, result in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

