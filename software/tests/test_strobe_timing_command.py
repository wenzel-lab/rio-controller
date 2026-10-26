"""Regression test: a repeated strobe 'timing' command must not make the wait grow.

On the Pi (PIC-paced mode) PiStrobeCam.set_timing() sends the PIC a wait equal to
the requested pre-padding plus the inter-frame dead time. The published
strobe_data["wait_ns"] is echoed back by clients (web UI, REST API) as the
pre-padding of the next timing command, so it must be the *requested* value,
not the derived hardware wait, otherwise every Set accumulates the dead time.
"""

import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["RIO_SIMULATION"] = "true"

from controllers.camera import Camera  # noqa: E402

DEAD_TIME_NS = 400_000  # typical inter-frame dead time added by PiStrobeCam


class _FakeStrobe:
    def get_cam_read_time(self):
        return True, 10_000


class _FakePicPacedStrobeCam:
    """Mimics PiStrobeCam in PIC-paced mode: hw wait = pre_padding + dead time."""

    def __init__(self):
        self.strobe = _FakeStrobe()
        self.strobe_wait_ns = 0
        self.strobe_period_ns = 0
        self.calls = []
        self._camera_type = "rpi"

    def set_timing(self, pre_padding_ns, strobe_period_ns, post_padding_ns):
        self.calls.append((pre_padding_ns, strobe_period_ns))
        self.strobe_wait_ns = pre_padding_ns + DEAD_TIME_NS
        self.strobe_period_ns = strobe_period_ns
        return True


def _bare_camera():
    cam = Camera.__new__(Camera)
    cam.strobe_cam = _FakePicPacedStrobeCam()
    cam.camera = object()
    cam.socketio = None
    cam._remote_strobe = False
    cam.strobe_period_ns = 5000
    cam.strobe_framerate = 30
    cam.cam_read_time_us = 0
    cam.exit_event = threading.Event()
    cam.thread = None
    cam.cam_data = {"camera": "rpi"}
    cam._video_recording = False
    cam._video_path = None
    cam.strobe_data = {"enable": 0, "hold": 0, "wait_ns": 0, "period_ns": 5000}
    return cam


class StrobeTimingCommandTest(unittest.TestCase):
    def _set_period(self, cam, period_ns):
        # Same shape the web UI / REST API send: echo the published wait_ns.
        cam.on_strobe(
            {
                "cmd": "timing",
                "parameters": {
                    "wait_ns": cam.strobe_data["wait_ns"],
                    "period_ns": period_ns,
                },
            }
        )

    def test_repeated_set_keeps_pre_padding_constant(self):
        cam = _bare_camera()
        for _ in range(3):
            self._set_period(cam, 100_000)

        pre_paddings = [c[0] for c in cam.strobe_cam.calls]
        self.assertEqual(pre_paddings, [0, 0, 0])
        self.assertEqual(cam.strobe_data["wait_ns"], 0)
        self.assertEqual(cam.strobe_data["period_ns"], 100_000)

    def test_user_pre_padding_is_preserved_across_period_sets(self):
        cam = _bare_camera()
        cam.on_strobe(
            {"cmd": "timing", "parameters": {"wait_ns": 50_000, "period_ns": 5000}}
        )
        self._set_period(cam, 20_000)
        self._set_period(cam, 20_000)

        pre_paddings = [c[0] for c in cam.strobe_cam.calls]
        self.assertEqual(pre_paddings, [50_000, 50_000, 50_000])
        self.assertEqual(cam.strobe_data["wait_ns"], 50_000)
        self.assertEqual(cam.strobe_data["period_ns"], 20_000)


if __name__ == "__main__":
    unittest.main()
