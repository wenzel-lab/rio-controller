"""
Segmentation module for droplet detection.

Handles contour detection and spatial filtering.
"""

import logging
import numpy as np
import cv2
from typing import List, Optional, Tuple

from .config import DropletDetectionConfig
from .utils import calculate_aspect_ratio

logger = logging.getLogger(__name__)


class Segmenter:
    """
    Segmentation module for droplet detection.

    Implements:
    - Contour extraction
    - Area-based filtering
    - Aspect ratio filtering
    - Spatial ROI filtering (channel band)
    """

    def __init__(self, config: DropletDetectionConfig):
        """
        Initialize segmenter with configuration.

        Args:
            config: DropletDetectionConfig instance
        """
        self.config = config

    def detect_contours(
        self, mask: np.ndarray, channel_band: Optional[Tuple[int, int]] = None
    ) -> List[np.ndarray]:
        """
        Extract and filter contours from binary mask.

        Args:
            mask: Binary mask (uint8, 0 or 255)
            channel_band: Optional tuple (y_min, y_max) for channel band filtering

        Returns:
            List of filtered contours
        """
        # Validate mask
        if not isinstance(mask, np.ndarray):
            logger.error(f"Mask must be numpy array, got {type(mask)}")
            return []
        if mask.dtype != np.uint8:
            logger.warning(f"Mask dtype is {mask.dtype}, expected uint8")

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        filtered = []

        for cnt in contours:
            # Area filtering
            area = cv2.contourArea(cnt)
            if area < self.config.min_area or area > self.config.max_area:
                continue

            # Bounding box for aspect ratio and spatial filtering
            x, y, w, h = cv2.boundingRect(cnt)

            # Aspect ratio filtering
            aspect_ratio = calculate_aspect_ratio(cnt)
            if (
                aspect_ratio < self.config.min_aspect_ratio
                or aspect_ratio > self.config.max_aspect_ratio
            ):
                continue

            # Spatial filtering (channel band)
            if channel_band is not None:
                y_min, y_max = channel_band
                # Check if contour centroid is within channel band (with margin)
                cy = y + h / 2
                margin = self.config.channel_band_margin
                if cy < (y_min - margin) or cy > (y_max + margin):
                    continue

            filtered.append(cnt)

        return filtered
