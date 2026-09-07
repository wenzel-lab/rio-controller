"""Unit tests for C++ backend ROI nearest-snap (no camera)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("numpy", MagicMock())

from drivers.camera.daheng_cpp_camera import DahengCppCamera, _snap_nearest  # noqa: E402


def test_snap_nearest_minimal_change():
    assert _snap_nearest(300, 16, 1440, 8) == 296  # nearer than 304
    assert _snap_nearest(301, 16, 1440, 8) == 304
    assert _snap_nearest(4, 16, 1440, 8) == 16
    assert _snap_nearest(17, 0, 100, 8) == 16


def test_validate_snaps_width_inc_8():
    cam = DahengCppCamera.__new__(DahengCppCamera)
    cam.config = {"OffsetX": 0, "OffsetY": 0, "Width": 1440, "Height": 1080}
    cam.get_max_resolution = lambda: (1440, 1080)
    cam.get_roi_constraints = lambda: {
        "offset_x": {"min": 0, "max": 1440, "increment": 8, "current": 0},
        "offset_y": {"min": 0, "max": 1080, "increment": 2, "current": 0},
        "width": {"min": 16, "max": 1440, "increment": 8, "current": 1440},
        "height": {"min": 2, "max": 1080, "increment": 2, "current": 1080},
        "sensor_width": 1440,
        "sensor_height": 1080,
    }
    x, y, w, h = cam.validate_and_snap_roi((101, 51, 300, 100))
    assert w == 296
    assert h == 100
    assert x % 8 == 0
    assert y % 2 == 0
    assert x + w <= 1440
    assert y + h <= 1080
