"""
Droplet Detection Module

Lightweight, real-time droplet detection algorithm for microfluidics.
Uses classical computer vision (OpenCV + NumPy) for Pi-compatible processing.
"""

from .detector import DropletDetector
from .preprocessor import Preprocessor
from .segmenter import Segmenter
from .measurer import Measurer, DropletMetrics
from .artifact_rejector import ArtifactRejector
from .histogram import DropletHistogram
from .config import DropletDetectionConfig, load_config, save_config, extract_droplet_config

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
