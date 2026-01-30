"""
Droplet Detection Module

Lightweight, real-time droplet detection algorithm for microfluidics.
Uses classical computer vision (OpenCV + NumPy) for Pi-compatible processing.
"""

try:
    from .detector import DropletDetector
    from .preprocessor import Preprocessor
    from .segmenter import Segmenter
    from .measurer import Measurer, DropletMetrics
    from .artifact_rejector import ArtifactRejector
    from .histogram import DropletHistogram
    from .config import DropletDetectionConfig, load_config, save_config, extract_droplet_config
except ImportError:  # pragma: no cover - allow direct file loading in tests
    import importlib
    import sys
    from pathlib import Path

    _base = Path(__file__).resolve().parent

    # Register this module as a package so submodule imports work
    sys.modules.setdefault("droplet_detection", sys.modules[__name__])
    __package__ = "droplet_detection"
    __path__ = [str(_base)]

    detector = importlib.import_module("droplet_detection.detector")
    preprocessor = importlib.import_module("droplet_detection.preprocessor")
    segmenter = importlib.import_module("droplet_detection.segmenter")
    measurer = importlib.import_module("droplet_detection.measurer")
    artifact_rejector = importlib.import_module("droplet_detection.artifact_rejector")
    histogram = importlib.import_module("droplet_detection.histogram")
    config = importlib.import_module("droplet_detection.config")

    DropletDetector = detector.DropletDetector
    Preprocessor = preprocessor.Preprocessor
    Segmenter = segmenter.Segmenter
    Measurer = measurer.Measurer
    DropletMetrics = measurer.DropletMetrics
    ArtifactRejector = artifact_rejector.ArtifactRejector
    DropletHistogram = histogram.DropletHistogram
    DropletDetectionConfig = config.DropletDetectionConfig
    load_config = config.load_config
    save_config = config.save_config
    extract_droplet_config = config.extract_droplet_config

__all__ = [
    "DropletDetector",
    "Preprocessor",
    "Segmenter",
    "Measurer",
    "DropletMetrics",
    "ArtifactRejector",
    "DropletHistogram",
    "DropletDetectionConfig",
    "load_config",
    "save_config",
    "extract_droplet_config",
]

__version__ = "0.1.0"
