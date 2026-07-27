"""Unit tests for Daheng ROI snap logic (mock cv2/numpy imports)."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("numpy", MagicMock())

from drivers.camera.daheng_camera import DahengCamera, _snap_to_increment  # noqa: E402


def test_snap_to_increment_floors():
    assert _snap_to_increment(17, 0, 100, 4) == 16
    assert _snap_to_increment(3, 8, 100, 4) == 8


class _SnapOnly(DahengCamera):
    def __init__(self):
        pass


def _cam(constraints):
    cam = _SnapOnly.__new__(_SnapOnly)
    cam._device = None
    cam.config = {}
    cam.get_max_resolution = lambda: (
        constraints["sensor_width"],
        constraints["sensor_height"],
    )
    cam.get_roi_constraints = lambda: constraints
    return cam


def test_validate_and_snap_clamps_to_sensor():
    c = {
        "offset_x": {"min": 0, "max": 1440, "increment": 2, "current": 100},
        "offset_y": {"min": 0, "max": 1080, "increment": 2, "current": 50},
        "width": {"min": 8, "max": 1440, "increment": 4, "current": 800},
        "height": {"min": 8, "max": 1080, "increment": 4, "current": 600},
        "sensor_width": 1440,
        "sensor_height": 1080,
        "stream_width": 800,
        "stream_height": 600,
    }
    cam = _cam(c)
    x, y, w, h = cam.validate_and_snap_roi((105, 55, 201, 151))
    assert x % 2 == 0
    assert y % 2 == 0
    assert w % 4 == 0
    assert h % 4 == 0
    assert x + w <= 1440
    assert y + h <= 1080


def test_snap_view_roi_matches_validate_absolute():
    c = {
        "offset_x": {"min": 0, "max": 1440, "increment": 2, "current": 0},
        "offset_y": {"min": 0, "max": 1080, "increment": 2, "current": 0},
        "width": {"min": 8, "max": 1440, "increment": 4, "current": 1440},
        "height": {"min": 8, "max": 1080, "increment": 4, "current": 1080},
        "sensor_width": 1440,
        "sensor_height": 1080,
        "stream_width": 1440,
        "stream_height": 1080,
    }
    cam = _cam(c)
    ox = SimpleNamespace(get=lambda: 0)
    oy = SimpleNamespace(get=lambda: 0)
    cam._device = SimpleNamespace(OffsetX=ox, OffsetY=oy)
    view = (100, 80, 401, 301)
    snapped = cam.snap_view_roi(view)
    abs_expected = cam.validate_and_snap_roi(view)
    assert snapped == (
        abs_expected[0],
        abs_expected[1],
        abs_expected[2],
        abs_expected[3],
    )

    c = {
        "offset_x": {"min": 0, "max": 1440, "increment": 2, "current": 200},
        "offset_y": {"min": 0, "max": 1080, "increment": 2, "current": 100},
        "width": {"min": 8, "max": 1440, "increment": 4, "current": 640},
        "height": {"min": 8, "max": 1080, "increment": 4, "current": 480},
        "sensor_width": 1440,
        "sensor_height": 1080,
        "stream_width": 640,
        "stream_height": 480,
    }
    cam = _cam(c)
    ox = SimpleNamespace(get=lambda: 200)
    oy = SimpleNamespace(get=lambda: 100)
    cam._device = SimpleNamespace(OffsetX=ox, OffsetY=oy)
    vx, vy, vw, vh = cam.snap_view_roi((10, 20, 300, 200))
    assert vx >= 0 and vy >= 0
    assert vw >= 8 and vh >= 8
    assert vx + vw <= 640
    assert vy + vh <= 480
