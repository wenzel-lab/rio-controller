"""
Timestamped H.264 output for picamera (legacy) / lab wall-clock video.

Mirrors the official Raspberry Pi recipe:
  rpicam-vid --save-pts timestamps.txt -o video.h264
  mkvmerge -o video.mkv --timecodes 0:timestamps.txt video.h264

Writes beside the bitstream:
  - .csv  — frame_index, pts_us, wall_ns, frame_size (analysis truth)
  - .pts  — mkvmerge timestamp format v2 (milliseconds)
"""

from __future__ import annotations

import csv
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

CSV_HEADER = ["frame_index", "pts_us", "wall_ns", "frame_size"]


@dataclass
class TimestampedRecordingResult:
    """Paths and metrics after closing a timestamped H.264 recording."""

    h264: str
    csv: str
    pts: str
    n_frames: int
    pts_first_us: Optional[int]
    pts_last_us: Optional[int]
    max_gap_ms: float
    mean_fps_pts: float
    playback_s: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "h264": self.h264,
            "csv": self.csv,
            "pts": self.pts,
            "n_frames": self.n_frames,
            "pts_first_us": self.pts_first_us,
            "pts_last_us": self.pts_last_us,
            "max_gap_ms": round(self.max_gap_ms, 3),
            "mean_fps_pts": round(self.mean_fps_pts, 3),
            "playback_s": round(self.playback_s, 3),
        }


def paths_for_h264(h264_path: str) -> Tuple[str, str, str]:
    """Return (h264, csv, pts) paths sharing the same stem."""
    stem = h264_path.rsplit(".", 1)[0] if "." in os.path.basename(h264_path) else h264_path
    if h264_path.lower().endswith(".h264"):
        stem = h264_path[:-5]
    return h264_path, f"{stem}.csv", f"{stem}.pts"


def write_pts_v2(path: str, pts_ms: Sequence[int]) -> None:
    """Write mkvmerge/libcamera-compatible timestamp file (format v2, ms)."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# timestamp format v2\n")
        for ms in pts_ms:
            fh.write(f"{int(ms)}\n")


def metrics_from_pts_us(pts_us: Sequence[int]) -> Dict[str, float]:
    """Compute playback duration / mean fps / max gap from PTS list (µs)."""
    n = len(pts_us)
    if n == 0:
        return {"n_frames": 0, "playback_s": 0.0, "mean_fps_pts": 0.0, "max_gap_ms": 0.0}
    if n == 1:
        return {"n_frames": 1, "playback_s": 0.0, "mean_fps_pts": 0.0, "max_gap_ms": 0.0}
    first = int(pts_us[0])
    last = int(pts_us[-1])
    playback_s = max(0.0, (last - first) / 1_000_000.0)
    gaps_ms = [(int(pts_us[i]) - int(pts_us[i - 1])) / 1000.0 for i in range(1, n)]
    max_gap_ms = max(gaps_ms) if gaps_ms else 0.0
    mean_fps = ((n - 1) / playback_s) if playback_s > 1e-9 else 0.0
    return {
        "n_frames": float(n),
        "playback_s": playback_s,
        "mean_fps_pts": mean_fps,
        "max_gap_ms": max_gap_ms,
    }


def load_pts_us_from_csv(csv_path: str) -> List[int]:
    """Load pts_us column from a timestamped recording CSV."""
    pts: List[int] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not row:
                continue
            raw = row.get("pts_us")
            if raw is None or raw == "":
                continue
            pts.append(int(float(raw)))
    return pts


class TimestampedH264Output:
    """
    File-like picamera output: writes annex-B H.264 and per-frame timestamps.

    Uses camera.frame (PiVideoFrame) when available. SPS / incomplete buffers
    with timestamp=None are skipped (same as picamera docs warn).
    """

    def __init__(self, h264_path: str, camera: Any = None) -> None:
        self.h264_path, self.csv_path, self.pts_path = paths_for_h264(h264_path)
        self.camera = camera
        parent = os.path.dirname(os.path.abspath(self.h264_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._fh = open(self.h264_path, "wb")
        self._csv_fh = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_fh)
        self._csv.writerow(CSV_HEADER)
        self._pts_us: List[int] = []
        self._closed = False

    def write(self, buf: bytes) -> int:
        if self._closed:
            raise ValueError("TimestampedH264Output is closed")
        if not buf:
            return 0
        self._fh.write(buf)
        fr = getattr(self.camera, "frame", None) if self.camera is not None else None
        if fr is None:
            return len(buf)
        complete = bool(getattr(fr, "complete", False))
        ts = getattr(fr, "timestamp", None)
        if not complete or ts is None:
            return len(buf)
        try:
            pts_us = int(ts)
        except (TypeError, ValueError):
            return len(buf)
        idx = getattr(fr, "index", None)
        if idx is None:
            idx = len(self._pts_us)
        frame_size = getattr(fr, "frame_size", None)
        if frame_size is None:
            frame_size = len(buf)
        wall_ns = time.monotonic_ns()
        self._csv.writerow([int(idx), pts_us, wall_ns, int(frame_size)])
        self._pts_us.append(pts_us)
        return len(buf)

    def flush(self) -> None:
        if self._closed:
            return
        self._fh.flush()
        self._csv_fh.flush()

    def close(self) -> TimestampedRecordingResult:
        if not self._closed:
            try:
                self.flush()
            finally:
                self._fh.close()
                self._csv_fh.close()
                self._closed = True
            write_pts_v2(self.pts_path, [p // 1000 for p in self._pts_us])
        m = metrics_from_pts_us(self._pts_us)
        return TimestampedRecordingResult(
            h264=self.h264_path,
            csv=self.csv_path,
            pts=self.pts_path,
            n_frames=int(m["n_frames"]),
            pts_first_us=self._pts_us[0] if self._pts_us else None,
            pts_last_us=self._pts_us[-1] if self._pts_us else None,
            max_gap_ms=float(m["max_gap_ms"]),
            mean_fps_pts=float(m["mean_fps_pts"]),
            playback_s=float(m["playback_s"]),
        )

    # picamera may call this
    def __enter__(self) -> "TimestampedH264Output":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def mux_h264_with_pts(
    h264_path: str,
    pts_path: str,
    *,
    mean_fps: float = 30.0,
    keep_h264: bool = True,
) -> Dict[str, Any]:
    """
    Mux annex-B H.264 + PTS sidecar into a playable container.

    Prefer mkvmerge (official Pi recipe). Fall back to ffmpeg with constant
    FPS derived from PTS mean (CSV/PTS remain the scientific truth).
    """
    if not h264_path or not os.path.isfile(h264_path):
        return {"ok": False, "error": "h264 missing", "path": None, "mux": None}
    if os.path.getsize(h264_path) < 32:
        return {"ok": False, "error": "h264 too small", "path": None, "mux": None}

    stem = h264_path[:-5] if h264_path.lower().endswith(".h264") else h264_path.rsplit(".", 1)[0]
    mkv_path = f"{stem}.mkv"
    mp4_path = f"{stem}.mp4"

    mkvmerge = shutil.which("mkvmerge")
    if mkvmerge and pts_path and os.path.isfile(pts_path):
        # Support both historic --timecodes and newer --timestamps
        for flag in ("--timecodes", "--timestamps"):
            cmd = [mkvmerge, "-o", mkv_path, flag, f"0:{pts_path}", h264_path]
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    timeout=180,
                    capture_output=True,
                    text=True,
                )
                if os.path.isfile(mkv_path) and os.path.getsize(mkv_path) > 0:
                    if not keep_h264:
                        _try_remove(h264_path)
                    return {
                        "ok": True,
                        "path": mkv_path,
                        "mux": "mkvmerge",
                        "command_flag": flag,
                    }
            except FileNotFoundError:
                break
            except Exception as e:
                logger.debug("mkvmerge %s failed: %s", flag, e)
                _try_remove(mkv_path)
                continue

    fps = max(1.0, min(float(mean_fps) or 30.0, 120.0))
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {
            "ok": False,
            "error": "neither mkvmerge nor ffmpeg available",
            "path": h264_path,
            "mux": None,
        }
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        f"{fps:.6f}",
        "-i",
        h264_path,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        mp4_path,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=180)
        if os.path.isfile(mp4_path) and os.path.getsize(mp4_path) > 0:
            if not keep_h264:
                _try_remove(h264_path)
            return {
                "ok": True,
                "path": mp4_path,
                "mux": "ffmpeg_fallback",
                "fps": round(fps, 3),
            }
    except Exception as e:
        logger.warning("ffmpeg PTS-fallback remux failed: %s", e)
    return {"ok": False, "error": "mux failed", "path": h264_path, "mux": None}


def _try_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
