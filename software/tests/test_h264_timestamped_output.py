"""Offline tests for timestamped H.264 output (no camera / picamera required)."""

from __future__ import annotations

import os
import sys
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock, patch

# Allow `python3 tests/test_h264_timestamped_output.py` from software/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.camera.h264_timestamped_output import (
    TimestampedH264Output,
    load_pts_us_from_csv,
    metrics_from_pts_us,
    mux_h264_with_pts,
    paths_for_h264,
    write_pts_v2,
)

FakeFrame = namedtuple(
    "FakeFrame",
    ["index", "frame_type", "frame_size", "video_size", "split_size", "timestamp", "complete"],
)


class FakeCamera:
    def __init__(self) -> None:
        self.frame = None


class TestH264TimestampedOutput(unittest.TestCase):
    def test_paths_for_h264(self):
        h, c, p = paths_for_h264("/tmp/video_2020.h264")
        self.assertTrue(h.endswith(".h264"))
        self.assertTrue(c.endswith(".csv"))
        self.assertTrue(p.endswith(".pts"))
        self.assertEqual(c.replace(".csv", ""), p.replace(".pts", ""))

    def test_metrics_from_pts_us_30fps(self):
        pts = [i * 33333 for i in range(31)]
        m = metrics_from_pts_us(pts)
        self.assertEqual(m["n_frames"], 31)
        self.assertGreaterEqual(m["playback_s"], 0.99)
        self.assertLessEqual(m["playback_s"], 1.01)
        self.assertGreaterEqual(m["mean_fps_pts"], 29.0)
        self.assertLessEqual(m["mean_fps_pts"], 31.0)
        self.assertAlmostEqual(m["max_gap_ms"], 33.333, delta=0.01)

    def test_write_and_close_skips_incomplete_and_none_ts(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            cam = FakeCamera()
            h264 = os.path.join(td, "clip.h264")
            out = TimestampedH264Output(h264, camera=cam)

            cam.frame = FakeFrame(0, 0, 10, 10, 10, None, False)
            out.write(b"\x00\x00\x00\x01\x67")

            cam.frame = FakeFrame(1, 0, 4, 14, 14, 0, True)
            out.write(b"\x00\x00\x00\x01\x65")

            cam.frame = FakeFrame(2, 0, 4, 18, 18, 33333, True)
            out.write(b"\x00\x00\x00\x01\x65")

            cam.frame = FakeFrame(3, 0, 4, 22, 22, None, True)
            out.write(b"\x00\x00\x00\x01\x65")

            result = out.close()
            self.assertEqual(result.n_frames, 2)
            self.assertEqual(result.pts_first_us, 0)
            self.assertEqual(result.pts_last_us, 33333)
            self.assertTrue(os.path.isfile(result.csv))
            self.assertTrue(os.path.isfile(result.pts))

            pts_us = load_pts_us_from_csv(result.csv)
            self.assertEqual(pts_us, [0, 33333])

            pts_text = Path(result.pts).read_text(encoding="utf-8")
            self.assertTrue(pts_text.startswith("# timestamp format v2\n"))
            self.assertIn("0\n", pts_text)
            self.assertIn("33\n", pts_text)

    def test_mux_prefers_mkvmerge(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            h264 = os.path.join(td, "v.h264")
            pts = os.path.join(td, "v.pts")
            with open(h264, "wb") as fh:
                fh.write(b"\x00" * 64)
            write_pts_v2(pts, [0, 33, 66])

            def fake_run(cmd, **kwargs):
                Path(cmd[2]).write_bytes(b"mkv")
                return MagicMock(returncode=0)

            with patch("drivers.camera.h264_timestamped_output.shutil.which") as which:
                which.side_effect = lambda name: "/bin/mkvmerge" if name == "mkvmerge" else None
                with patch(
                    "drivers.camera.h264_timestamped_output.subprocess.run",
                    side_effect=fake_run,
                ):
                    result = mux_h264_with_pts(h264, pts, mean_fps=30.0, keep_h264=True)

            self.assertTrue(result["ok"])
            self.assertEqual(result["mux"], "mkvmerge")
            self.assertTrue(result["path"].endswith(".mkv"))
            self.assertTrue(os.path.isfile(result["path"]))

    def test_mux_ffmpeg_fallback(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            h264 = os.path.join(td, "v.h264")
            pts = os.path.join(td, "v.pts")
            with open(h264, "wb") as fh:
                fh.write(b"\x00" * 64)
            write_pts_v2(pts, [0, 40, 80])

            def fake_run(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b"mp4")
                return MagicMock(returncode=0)

            with patch("drivers.camera.h264_timestamped_output.shutil.which") as which:
                which.side_effect = lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None
                with patch(
                    "drivers.camera.h264_timestamped_output.subprocess.run",
                    side_effect=fake_run,
                ):
                    result = mux_h264_with_pts(h264, pts, mean_fps=25.0, keep_h264=True)

            self.assertTrue(result["ok"])
            self.assertEqual(result["mux"], "ffmpeg_fallback")
            self.assertTrue(result["path"].endswith(".mp4"))


if __name__ == "__main__":
    unittest.main()
