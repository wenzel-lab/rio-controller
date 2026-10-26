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

# Per-frame timestamp sidecars are moved here after a successful mux (not left next
# to the video) so they can be inspected offline from the SD card: ~/rio-controller/diag
DIAG_DIR = os.path.join(os.path.expanduser("~"), "rio-controller", "diag")


def _stash_sidecar(path: str) -> None:
    """Move a sidecar file into DIAG_DIR (fallback: delete)."""
    if not path or not os.path.isfile(path):
        return
    try:
        os.makedirs(DIAG_DIR, exist_ok=True)
        shutil.move(path, os.path.join(DIAG_DIR, os.path.basename(path)))
    except Exception as e:
        logger.warning("Could not stash %s into %s: %s", path, DIAG_DIR, e)
        _try_remove(path)


def _nal_stats(h264_path: str) -> Optional[int]:
    """Log NAL-unit counts of the raw Annex-B stream; return the picture count
    (slices with first_mb_in_slice == 0) or None if the scan failed."""
    counts: Dict[int, int] = {}
    first_mb_zero = 0
    try:
        with open(h264_path, "rb") as fh:
            data = fh.read()
        i = 0
        n = len(data)
        while True:
            j = data.find(b"\x00\x00\x01", i)
            if j < 0 or j + 3 >= n:
                break
            hdr = data[j + 3]
            t = hdr & 0x1F
            counts[t] = counts.get(t, 0) + 1
            # slice NAL (1/5): first_mb_in_slice is ue(v) at bit 0 of the slice header;
            # a leading '1' bit means first_mb_in_slice == 0 (start of a new picture).
            if t in (1, 5) and j + 4 < n and (data[j + 4] & 0x80):
                first_mb_zero += 1
            i = j + 3
        logger.info(
            "H.264 NAL stats %s: bytes=%d nal_types=%s slices_first_mb0=%d",
            h264_path, n, dict(sorted(counts.items())), first_mb_zero,
        )
        return first_mb_zero
    except Exception as e:
        logger.warning("NAL stats failed for %s: %s", h264_path, e)
        return None


def _read_pts_v2_ms(path: str) -> List[int]:
    out: List[int] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                out.append(int(float(line)))
            except ValueError:
                continue
    return out


def _median_gap_ms(pts_ms: Sequence[int], default: int = 20) -> int:
    gaps = sorted(b - a for a, b in zip(pts_ms, pts_ms[1:]) if b > a)
    return gaps[len(gaps) // 2] if gaps else default


def _reconcile_pts_with_frames(pts_path: str, n_frames: Optional[int]) -> None:
    """
    Make the timestamp file have exactly one entry per H.264 picture.

    mkvmerge requires this. With fewer timestamps than frames it extrapolates the
    leftovers far beyond the end (observed: a 70 s recording became a 140 s file,
    playback stops at 70 s). Missing entries are appended at the median frame gap;
    extras are dropped. Both cases are logged for the SD-card log.
    """
    if not n_frames or not pts_path or not os.path.isfile(pts_path):
        return
    try:
        pts_ms = _read_pts_v2_ms(pts_path)
    except Exception as e:
        logger.warning("PTS reconcile: cannot read %s: %s", pts_path, e)
        return
    n_pts = len(pts_ms)
    if n_pts == n_frames or n_pts == 0:
        return
    gap = _median_gap_ms(pts_ms)
    if n_pts < n_frames:
        missing = n_frames - n_pts
        last = pts_ms[-1]
        pts_ms.extend(last + gap * (i + 1) for i in range(missing))
        logger.warning(
            "PTS reconcile %s: %d timestamps for %d frames -> appended %d at %d ms gap",
            pts_path, n_pts, n_frames, missing, gap,
        )
    else:
        logger.warning(
            "PTS reconcile %s: %d timestamps for %d frames -> dropped %d trailing",
            pts_path, n_pts, n_frames, n_pts - n_frames,
        )
        pts_ms = pts_ms[:n_frames]
    try:
        write_pts_v2(pts_path, pts_ms)
    except Exception as e:
        logger.warning("PTS reconcile: cannot rewrite %s: %s", pts_path, e)


def _mkv_to_mp4(mkv_path: str, mp4_path: str) -> bool:
    """
    Rewrap the mkvmerge output as .mp4 with ffmpeg stream copy (-c copy): the
    H.264 frames and their per-frame timestamps are copied unchanged, nothing is
    re-encoded (no -r/-framerate, which would discard the stored timestamps).
    Returns True only if the .mp4 was written; on failure any partial .mp4 is removed.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg not available; keeping %s", mkv_path)
        return False
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-i", mkv_path, "-c", "copy", "-movflags", "+faststart", mp4_path]
    try:
        proc = subprocess.run(cmd, check=False, timeout=180, capture_output=True, text=True)
    except Exception as e:
        logger.warning("ffmpeg mkv->mp4 failed (%s); keeping %s", e, mkv_path)
        _try_remove(mp4_path)
        return False
    if proc.returncode == 0 and os.path.isfile(mp4_path) and os.path.getsize(mp4_path) > 0:
        return True
    logger.warning(
        "ffmpeg mkv->mp4 rc=%s (%s); keeping %s",
        proc.returncode, (proc.stderr or "").strip()[-300:], mkv_path,
    )
    _try_remove(mp4_path)
    return False


def _probe_container(path: str) -> None:
    """Log what the container itself claims (fps/frames/duration) — offline diagnosis."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
             "-show_entries", "stream=r_frame_rate,avg_frame_rate,nb_read_frames,duration:format=duration",
             "-of", "default=nw=1", path],
            capture_output=True, text=True, timeout=120,
        )
        logger.info("ffprobe %s: %s %s", path, " ".join(proc.stdout.split()), proc.stderr.strip()[-300:])
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", path, e)


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
        if not complete:
            return len(buf)
        # SPS/PPS header buffers are not pictures (picamera frame_type 2).
        if getattr(fr, "frame_type", None) == 2:
            return len(buf)
        ts = getattr(fr, "timestamp", None)
        if ts is None:
            # picamera maps buf.pts == 0 (and MMAL_TIME_UNKNOWN) to None. With the
            # default clock reset the FIRST picture really is at t=0; skipping it
            # left the .pts one entry short and mkvmerge doubled the file duration.
            if not self._pts_us:
                pts_us = 0
            else:
                gap = (self._pts_us[-1] - self._pts_us[-2]) if len(self._pts_us) >= 2 else 20000
                pts_us = self._pts_us[-1] + max(1, gap)
            logger.info(
                "H.264 picture without PTS (frame index=%s); assigned %d us",
                getattr(fr, "index", None), pts_us,
            )
        else:
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
    cleanup_sidecars: bool = False,
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

    n_frames = _nal_stats(h264_path)
    _reconcile_pts_with_frames(pts_path, n_frames)
    stem = h264_path[:-5] if h264_path.lower().endswith(".h264") else h264_path.rsplit(".", 1)[0]
    mkv_path = f"{stem}.mkv"
    mp4_path = f"{stem}.mp4"

    stem_csv = f"{stem}.csv"

    def _finish(path: str, mode: str, **extra: Any) -> Dict[str, Any]:
        if not keep_h264:
            _try_remove(h264_path)
        if cleanup_sidecars:
            # Timestamps now live inside the container; keep the .pts/.csv in DIAG_DIR.
            _stash_sidecar(pts_path)
            _stash_sidecar(stem_csv)
        _probe_container(path)
        out = {"ok": True, "path": path, "mux": mode}
        out.update(extra)
        return out

    mkvmerge = shutil.which("mkvmerge")
    if mkvmerge and pts_path and os.path.isfile(pts_path):
        # Support both historic --timecodes and newer --timestamps.
        # mkvmerge exit codes: 0 = ok, 1 = finished WITH WARNINGS (file is valid),
        # 2 = error. Treat 1 as success when the output exists (check=True would
        # otherwise discard a good .mkv and fall back to a constant-fps .mp4).
        for flag in ("--timecodes", "--timestamps"):
            cmd = [mkvmerge, "-o", mkv_path, flag, f"0:{pts_path}", h264_path]
            try:
                proc = subprocess.run(
                    cmd,
                    check=False,
                    timeout=180,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError:
                break
            except Exception as e:
                logger.warning("mkvmerge %s failed: %s", flag, e)
                _try_remove(mkv_path)
                continue
            if proc.returncode in (0, 1) and os.path.isfile(mkv_path) and os.path.getsize(mkv_path) > 0:
                logger.info(
                    "mkvmerge rc=%s output: %s",
                    proc.returncode,
                    " ".join((proc.stdout or "").split())[-600:],
                )
                if proc.returncode == 1:
                    logger.warning(
                        "mkvmerge finished with warnings (kept .mkv): %s",
                        (proc.stdout or proc.stderr or "").strip()[-400:],
                    )
                if _mkv_to_mp4(mkv_path, mp4_path):
                    _try_remove(mkv_path)
                    return _finish(mp4_path, "mkvmerge+mp4", command_flag=flag, returncode=proc.returncode)
                return _finish(mkv_path, "mkvmerge", command_flag=flag, returncode=proc.returncode)
            logger.warning(
                "mkvmerge %s rc=%s: %s",
                flag,
                proc.returncode,
                (proc.stderr or proc.stdout or "").strip()[-400:],
            )
            _try_remove(mkv_path)

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
            return _finish(mp4_path, "ffmpeg_fallback", fps=round(fps, 3))
    except Exception as e:
        logger.warning("ffmpeg PTS-fallback remux failed: %s", e)
    return {"ok": False, "error": "mux failed", "path": h264_path, "mux": None}


def _try_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
