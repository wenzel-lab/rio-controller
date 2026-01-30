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
import time

from path_bootstrap import bootstrap_runtime

bootstrap_runtime()

# Note: This test file may need updating for new structure
from drivers.camera import create_camera, BaseCamera  # noqa: E402
import numpy as np  # noqa: F401, E402


def test_camera_creation():
    """Test camera factory function"""
    print("Testing camera creation...")
    camera = create_camera(simulation=True)
    assert camera is not None
    print(f"✓ Camera created: {type(camera).__name__}")


def test_camera_start_stop(camera: BaseCamera):
    """Test camera start/stop"""
    print("\nTesting camera start/stop...")
    camera.start()
    print("✓ Camera started")
    camera.stop()
    print("✓ Camera stopped")


def test_frame_capture(camera: BaseCamera):
    """Test single frame capture"""
    print("\nTesting frame capture...")
    camera.start()
    frame = None
    for _ in range(50):
        frame = camera.get_frame_array()
        if frame is not None:
            break
        time.sleep(0.02)
    assert frame is not None
    print(f"✓ Frame captured: shape={frame.shape}, dtype={frame.dtype}")
    camera.stop()


def test_roi_capture(camera: BaseCamera):
    """Test ROI capture"""
    print("\nTesting ROI capture...")
    camera.start()
    # Test ROI: (x, y, width, height) = (100, 100, 200, 150)
    roi = (100, 100, 200, 150)
    roi_frame = None
    for _ in range(50):
        roi_frame = camera.get_frame_roi(roi)
        if roi_frame is not None:
            break
        time.sleep(0.02)
    assert roi_frame is not None
    print(f"✓ ROI captured: shape={roi_frame.shape}, expected=(150, 200, 3)")
    camera.stop()


def test_configuration(camera: BaseCamera):
    """Test camera configuration"""
    print("\nTesting configuration...")
    config = {"Width": 640, "Height": 480, "FrameRate": 30}
    camera.set_config(config)
    print("✓ Configuration set")


def main():
    """Run all tests"""
    print("=" * 50)
    print("Camera Abstraction Layer Test")
    print("=" * 50)

    camera = create_camera(simulation=True)
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
            test_func()
            results.append((name, True))
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
    except Exception:
        pass

    # Exit code
    all_passed = all(result for _, result in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
