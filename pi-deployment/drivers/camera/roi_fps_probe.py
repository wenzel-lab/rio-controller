#!/usr/bin/env python3
"""
ROI FPS probe for Raspberry Pi camera backends.

Usage examples (run on Pi, from software/ or pi-deployment/):
  python drivers/camera/roi_fps_probe.py --mode stream --fps 30,60 --resolution 640x480
  python drivers/camera/roi_fps_probe.py --mode stream --fps 30,60,90 --roi 0,0,640,480 --roi-mode hardware
  python drivers/camera/roi_fps_probe.py --mode roi --fps 60 --roi 200,200,320,240 --roi-mode hardware

Notes:
  - "stream" mode measures generate_frames() throughput (JPEG stream, like web UI).
  - "full" mode measures get_frame_array() throughput (raw capture).
  - "roi" mode measures get_frame_roi() throughput (ROI analysis path).
  - Hardware ROI is only applied if the backend implements set_roi_hardware().
"""

from __future__ import annotations

import argparse
import time
from typing import Iterable, Tuple, Optional

from path_bootstrap import bootstrap_runtime

bootstrap_runtime()

from drivers.camera import create_camera  # noqa: E402


def parse_int_list(value: str) -> list[int]:
    return [int(v.strip()) for v in value.split(",") if v.strip()]


def parse_resolution(value: str) -> Tuple[int, int]:
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise ValueError("Resolution must be in the form WIDTHxHEIGHT (e.g. 640x480)")
    return int(parts[0]), int(parts[1])


def parse_roi(value: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise ValueError("ROI must be in the form x,y,width,height (e.g. 100,100,320,240)")
    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])


def _get_max_resolution(camera) -> Tuple[int, int]:
    if hasattr(camera, "get_max_resolution"):
        try:
            return camera.get_max_resolution()
        except Exception:
            pass
    size = camera.config.get("size", [640, 480])
    return int(size[0]), int(size[1])


def _apply_config(camera, width: Optional[int], height: Optional[int], fps: Optional[int]) -> None:
    config = {}
    if width and height:
        config["Width"] = width
        config["Height"] = height
    if fps:
        config["FrameRate"] = fps
    if config:
        camera.set_config(config)


def _apply_roi_mode(camera, roi: Optional[Tuple[int, int, int, int]], roi_mode: str) -> None:
    if roi_mode == "none":
        if hasattr(camera, "set_roi_hardware"):
            max_w, max_h = _get_max_resolution(camera)
            camera.set_roi_hardware((0, 0, max_w, max_h))
        return
    if roi is None:
        return
    if roi_mode == "hardware":
        if hasattr(camera, "set_roi_hardware"):
            ok = bool(camera.set_roi_hardware(roi))
            print(f"Hardware ROI set: {ok} -> {roi}")
        else:
            print("Hardware ROI requested, but backend lacks set_roi_hardware().")


def _measure_stream(camera, duration_s: float, warmup_s: float) -> Tuple[int, float, float]:
    gen = camera.generate_frames()
    start = time.time()
    frames = 0
    while time.time() - start < warmup_s:
        next(gen)
    start = time.time()
    while time.time() - start < duration_s:
        next(gen)
        frames += 1
    elapsed = time.time() - start
    gen.close()
    return frames, elapsed, frames / elapsed if elapsed > 0 else 0.0


def _measure_full(camera, duration_s: float, warmup_s: float) -> Tuple[int, float, float]:
    start = time.time()
    frames = 0
    while time.time() - start < warmup_s:
        camera.get_frame_array()
    start = time.time()
    while time.time() - start < duration_s:
        camera.get_frame_array()
        frames += 1
    elapsed = time.time() - start
    return frames, elapsed, frames / elapsed if elapsed > 0 else 0.0


def _measure_roi(camera, roi: Tuple[int, int, int, int], duration_s: float, warmup_s: float) -> Tuple[int, float, float]:
    start = time.time()
    frames = 0
    while time.time() - start < warmup_s:
        camera.get_frame_roi(roi)
    start = time.time()
    while time.time() - start < duration_s:
        camera.get_frame_roi(roi)
        frames += 1
    elapsed = time.time() - start
    return frames, elapsed, frames / elapsed if elapsed > 0 else 0.0


def _print_camera_state(camera) -> None:
    actual_fps = None
    if hasattr(camera, "get_actual_framerate"):
        try:
            actual_fps = float(camera.get_actual_framerate())
        except Exception:
            actual_fps = None
    shutter = None
    if hasattr(camera, "get_actual_shutter_speed"):
        try:
            shutter = int(camera.get_actual_shutter_speed())
        except Exception:
            shutter = None
    print(
        f"Camera config: size={camera.config.get('size')} "
        f"FrameRate={camera.config.get('FrameRate')} "
        f"ShutterSpeed={camera.config.get('ShutterSpeed')} "
        f"actual_fps={actual_fps} shutter_us={shutter}"
    )


def run_probe(
    camera_type: Optional[str],
    fps_list: Iterable[int],
    resolution: Optional[Tuple[int, int]],
    roi: Optional[Tuple[int, int, int, int]],
    roi_mode: str,
    duration_s: float,
    warmup_s: float,
    mode: str,
) -> None:
    camera = create_camera(camera_type=camera_type)
    print(f"Camera: {type(camera).__name__}")

    width = resolution[0] if resolution else None
    height = resolution[1] if resolution else None

    for fps in fps_list:
        print("\n" + "=" * 60)
        print(f"Target FPS: {fps}")
        _apply_config(camera, width, height, fps)
        _apply_roi_mode(camera, roi, roi_mode)
        _print_camera_state(camera)

        if mode in ("stream", "all"):
            frames, elapsed, fps_meas = _measure_stream(camera, duration_s, warmup_s)
            print(f"STREAM: {frames} frames in {elapsed:.2f}s -> {fps_meas:.1f} fps")

        if mode in ("full", "all"):
            frames, elapsed, fps_meas = _measure_full(camera, duration_s, warmup_s)
            print(f"FULL:   {frames} frames in {elapsed:.2f}s -> {fps_meas:.1f} fps")

        if mode in ("roi", "all"):
            if roi is None:
                print("ROI: skipped (no ROI provided)")
            else:
                frames, elapsed, fps_meas = _measure_roi(camera, roi, duration_s, warmup_s)
                print(f"ROI:    {frames} frames in {elapsed:.2f}s -> {fps_meas:.1f} fps")

    try:
        camera.close()
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="ROI FPS probe for camera backends.")
    parser.add_argument("--camera-type", default=None, help="rpi, mako, daheng, or auto")
    parser.add_argument("--fps", default="30,60", help="Comma-separated FPS list")
    parser.add_argument("--resolution", default=None, help="WIDTHxHEIGHT (e.g. 640x480)")
    parser.add_argument("--roi", default=None, help="x,y,width,height (e.g. 100,100,320,240)")
    parser.add_argument(
        "--roi-mode",
        default="none",
        choices=["none", "software", "hardware"],
        help="Apply hardware ROI if supported",
    )
    parser.add_argument("--duration", type=float, default=5.0, help="Measurement window (s)")
    parser.add_argument("--warmup", type=float, default=1.0, help="Warmup window (s)")
    parser.add_argument(
        "--mode",
        default="stream",
        choices=["stream", "full", "roi", "all"],
        help="What to measure",
    )
    args = parser.parse_args()

    fps_list = parse_int_list(args.fps)
    resolution = parse_resolution(args.resolution) if args.resolution else None
    roi = parse_roi(args.roi) if args.roi else None

    run_probe(
        camera_type=args.camera_type if args.camera_type != "auto" else None,
        fps_list=fps_list,
        resolution=resolution,
        roi=roi,
        roi_mode=args.roi_mode,
        duration_s=args.duration,
        warmup_s=args.warmup,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
