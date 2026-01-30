"""
Droplet detection test using a synthetic image.
"""

import importlib.util
import os
import sys

import numpy as np


def _load_droplet_detection():
    base_dir = os.path.join(os.path.dirname(__file__))
    init_path = os.path.join(base_dir, "__init__.py")
    spec = importlib.util.spec_from_file_location("droplet_detection", init_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["droplet_detection"] = module
    spec.loader.exec_module(module)
    return module


def _make_synthetic_image(width: int, height: int) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    yy, xx = np.ogrid[:height, :width]
    cy, cx = height // 2, width // 2
    radius = min(width, height) // 8
    mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
    image[mask] = [255, 255, 255]
    return image


def test_detector_on_synthetic_image():
    droplet_detection = _load_droplet_detection()
    DropletDetector = droplet_detection.DropletDetector
    DropletDetectionConfig = droplet_detection.DropletDetectionConfig
    DropletHistogram = droplet_detection.DropletHistogram

    image = _make_synthetic_image(320, 240)
    roi = (60, 80, 200, 80)
    roi_image = image[roi[1] : roi[1] + roi[3], roi[0] : roi[0] + roi[2]]

    config = DropletDetectionConfig()
    detector = DropletDetector(roi, config)

    for _ in range(config.background_frames):
        detector.preprocessor.initialize_background(roi_image)

    metrics = detector.process_frame(roi_image)
    assert isinstance(metrics, list)

    histogram = DropletHistogram(pixel_ratio=1.0, unit="px")
    histogram.update(metrics)
    stats = histogram.get_statistics()
    assert "count" in stats
