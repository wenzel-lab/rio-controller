"""
Configuration and parameter profile management for droplet detection.

Provides default configurations and JSON-based parameter profile management.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DropletDetectionConfig:
    """
    Configuration class for droplet detection parameters.

    Manages all tunable parameters for the detection pipeline including
    preprocessing, segmentation, measurement, and artifact rejection.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration with defaults or provided values.

        Args:
            config_dict: Optional dictionary of configuration values
        """
        # Preprocessing parameters
        self.background_method: str = "static"  # "static" or "highpass"
        self.background_frames: int = 30  # Number of frames for static background
        self.gaussian_blur_kernel: tuple = (11, 11)  # Kernel size for high-pass
        self.threshold_method: str = "otsu"  # "otsu" or "adaptive"
        self.adaptive_block_size: int = 11  # For adaptive thresholding
        self.adaptive_C: int = 2  # For adaptive thresholding
        self.morph_kernel_size: tuple = (3, 3)  # Morphological kernel size
        self.morph_operation: str = "open"  # "open", "close", or "both"

        # Segmentation parameters
        self.min_area: int = 20  # Minimum contour area in pixels²
        self.max_area: int = 5000  # Maximum contour area in pixels²
        self.min_aspect_ratio: float = 0.5  # Minimum aspect ratio (allow round droplets ~1.0)
        self.max_aspect_ratio: float = 3.0  # Maximum aspect ratio (allow some elliptical)
        self.channel_band_margin: int = 10  # Margin for channel band filtering (pixels)

        # Artifact rejection parameters
        self.min_motion: float = (
            0.5  # Minimum motion in pixels (frame-to-frame) - lowered for better detection
        )
        self.max_perp_drift: float = 5.0  # Maximum perpendicular drift (pixels)
        self.use_frame_diff: bool = False  # Use frame difference method
        self.frame_diff_threshold: int = 30  # Threshold for frame difference

        # Measurement parameters
        self.min_contour_points: int = 5  # Minimum points for ellipse fitting

        # Histogram parameters
        self.histogram_window_size: int = (
            2000  # Maximum number of measurements in histogram (sliding window)
        )
        self.histogram_bins: int = 40  # Number of bins for histogram

        # Calibration parameters
        self.pixel_ratio: float = 1.0  # um per pixel (calibration factor)

        # Update with provided config if available
        if config_dict:
            self.update(config_dict)

    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary.

        Args:
            config_dict: Dictionary of configuration values to update
        """
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown configuration key: {key}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "background_method": self.background_method,
            "background_frames": self.background_frames,
            "gaussian_blur_kernel": self.gaussian_blur_kernel,
            "threshold_method": self.threshold_method,
            "adaptive_block_size": self.adaptive_block_size,
            "adaptive_C": self.adaptive_C,
            "morph_kernel_size": self.morph_kernel_size,
            "morph_operation": self.morph_operation,
            "min_area": self.min_area,
            "max_area": self.max_area,
            "min_aspect_ratio": self.min_aspect_ratio,
            "max_aspect_ratio": self.max_aspect_ratio,
            "channel_band_margin": self.channel_band_margin,
            "min_motion": self.min_motion,
            "max_perp_drift": self.max_perp_drift,
            "use_frame_diff": self.use_frame_diff,
            "frame_diff_threshold": self.frame_diff_threshold,
            "min_contour_points": self.min_contour_points,
            "histogram_window_size": self.histogram_window_size,
            "histogram_bins": self.histogram_bins,
            "pixel_ratio": self.pixel_ratio,
        }

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration parameters.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate background method
        if self.background_method not in ["static", "highpass"]:
            errors.append(f"Invalid background_method: {self.background_method}")

        # Validate histogram parameters
        if self.histogram_window_size < 1:
            errors.append("histogram_window_size must be >= 1")
        if self.histogram_bins < 1:
            errors.append("histogram_bins must be >= 1")

        # Validate threshold method
        if self.threshold_method not in ["otsu", "adaptive"]:
            errors.append(f"Invalid threshold_method: {self.threshold_method}")

        # Validate morphological operation
        if self.morph_operation not in ["open", "close", "both"]:
            errors.append(f"Invalid morph_operation: {self.morph_operation}")

        # Validate ranges
        if self.min_area < 0:
            errors.append("min_area must be >= 0")
        if self.max_area <= self.min_area:
            errors.append("max_area must be > min_area")
        if self.min_aspect_ratio <= 0:
            errors.append("min_aspect_ratio must be > 0")
        if self.max_aspect_ratio <= self.min_aspect_ratio:
            errors.append("max_aspect_ratio must be > min_aspect_ratio")
        if self.min_motion < 0:
            errors.append("min_motion must be >= 0")
        if self.max_perp_drift < 0:
            errors.append("max_perp_drift must be >= 0")

        return len(errors) == 0, errors


def extract_droplet_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract droplet detection configuration from nested or flat structure.

    Supports both formats:
    - Nested: {"modules": {"droplet_analysis": true}, "droplet_detection": {...}}
    - Flat: {"histogram_window_size": 2000, ...}

    Args:
        config_dict: Configuration dictionary (nested or flat)

    Returns:
        Flat dictionary with droplet detection parameters
    """
    # Check for nested structure
    if "droplet_detection" in config_dict:
        # Nested structure: extract from droplet_detection key
        droplet_config = config_dict["droplet_detection"]
        if not isinstance(droplet_config, dict):
            raise ValueError("'droplet_detection' must be a dictionary")
        return droplet_config.copy()

    # Check if this looks like a flat droplet detection config
    # (has at least one known droplet detection parameter)
    known_params = {
        "histogram_window_size",
        "histogram_bins",
        "min_area",
        "max_area",
        "background_method",
        "threshold_method",
        "pixel_ratio",
    }
    if any(key in config_dict for key in known_params):
        # Flat structure: return as-is
        return config_dict.copy()

    # Unknown structure: return empty dict (will use defaults)
    logger.warning(
        "No droplet_detection section found and no known parameters detected. Using defaults."
    )
    return {}


def load_config(filepath: str) -> DropletDetectionConfig:
    """
    Load configuration from JSON file.

    Supports both nested and flat configuration structures:

    Nested structure:
    {
      "modules": {
        "droplet_analysis": true
      },
      "droplet_detection": {
        "histogram_window_size": 2000,
        "histogram_bins": 40,
        ...
      }
    }

    Flat structure (backward compatible):
    {
      "histogram_window_size": 2000,
      "histogram_bins": 40,
      ...
    }

    Args:
        filepath: Path to JSON configuration file

    Returns:
        DropletDetectionConfig instance
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(path, "r") as f:
        config_dict = json.load(f)

    # Extract droplet detection config (handles both nested and flat)
    droplet_config = extract_droplet_config(config_dict)

    config = DropletDetectionConfig(droplet_config)
    is_valid, errors = config.validate()
    if not is_valid:
        logger.warning(f"Configuration validation errors: {errors}")

    return config


def save_config(
    config: DropletDetectionConfig,
    filepath: str,
    nested: bool = False,
    include_modules: bool = False,
) -> None:
    """
    Save configuration to JSON file.

    Supports both nested and flat output formats:

    Nested format (nested=True):
    {
      "modules": {
        "droplet_analysis": true
      },
      "droplet_detection": {
        "histogram_window_size": 2000,
        ...
      }
    }

    Flat format (nested=False, default for backward compatibility):
    {
      "histogram_window_size": 2000,
      ...
    }

    Args:
        config: DropletDetectionConfig instance to save
        filepath: Path to save JSON configuration file
        nested: If True, save in nested structure. If False, save flat (default)
        include_modules: If True and nested=True, include modules section
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    is_valid, errors = config.validate()
    if not is_valid:
        logger.warning(f"Saving configuration with validation errors: {errors}")

    config_dict = config.to_dict()

    if nested:
        # Save in nested structure
        output = {}
        if include_modules:
            output["modules"] = {"droplet_analysis": True}
        output["droplet_detection"] = config_dict
        with open(path, "w") as f:
            json.dump(output, f, indent=2)
    else:
        # Save in flat structure (backward compatible)
        with open(path, "w") as f:
            json.dump(config_dict, f, indent=2)


# Default configuration profiles
DEFAULT_CONFIG = DropletDetectionConfig()

# Example profiles for different scenarios
PROFILE_SMALL_DROPLETS = DropletDetectionConfig(
    {
        "min_area": 10,
        "max_area": 1000,
        "min_aspect_ratio": 1.2,
        "max_aspect_ratio": 8.0,
    }
)

PROFILE_LARGE_DROPLETS = DropletDetectionConfig(
    {
        "min_area": 100,
        "max_area": 10000,
        "min_aspect_ratio": 2.0,
        "max_aspect_ratio": 15.0,
    }
)

PROFILE_HIGH_DENSITY = DropletDetectionConfig(
    {
        "min_area": 20,
        "max_area": 5000,
        "min_aspect_ratio": 1.5,
        "max_aspect_ratio": 10.0,
        "morph_kernel_size": (5, 5),  # Larger kernel for better separation
    }
)
