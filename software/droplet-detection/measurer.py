"""
Measurement module for droplet detection.

Calculates geometric metrics for detected droplets.
"""

import logging
import numpy as np
import cv2
from typing import List, Tuple
from dataclasses import dataclass

from .config import DropletDetectionConfig
from .utils import get_contour_centroid

logger = logging.getLogger(__name__)


@dataclass
class DropletMetrics:
    """
    Metrics for a single detected droplet.

    Attributes:
        area: Contour area in pixels²
        major_axis: Major axis length from ellipse fitting (pixels)
        equivalent_diameter: Equivalent diameter (pixels)
        centroid: Centroid coordinates (x, y)
        bounding_box: Bounding box (x, y, width, height)
        aspect_ratio: Aspect ratio of bounding box
    """

    area: float
    major_axis: float
    equivalent_diameter: float
    centroid: Tuple[float, float]
    bounding_box: Tuple[int, int, int, int]
    aspect_ratio: float


class Measurer:
    """
    Measurement module for droplet detection.

    Calculates geometric metrics for each detected contour:
    - Ellipse fitting (major axis = droplet length)
    - Equivalent diameter
    - Area
    - Centroid
    - Bounding box
    """

    def __init__(self, config: DropletDetectionConfig):
        """
        Initialize measurer with configuration.

        Args:
            config: DropletDetectionConfig instance
        """
        self.config = config

    def measure(self, contours: List[np.ndarray], radius_offset_px: float = 0.0) -> List[DropletMetrics]:
        """
        Calculate metrics for each contour.

        Args:
            contours: List of contours from cv2.findContours
            radius_offset_px: Pixel offset to correct for threshold bias (default: 0.0)

        Returns:
            List of DropletMetrics objects
        """
        metrics = []

        for cnt in contours:
            try:
                # Area
                area = cv2.contourArea(cnt)
                if area == 0:
                    continue

                # Bounding box
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = max(w, h) / max(1, min(w, h))

                # Centroid
                centroid = get_contour_centroid(cnt)

                # Ellipse fitting (for major axis)
                if len(cnt) >= self.config.min_contour_points:
                    try:
                        ellipse = cv2.fitEllipse(cnt)
                        # ellipse[1] is (width, height) of ellipse
                        major_axis = max(ellipse[1])
                    except cv2.error:
                        # Fallback to bounding box if ellipse fitting fails
                        major_axis = max(w, h)
                else:
                    # Not enough points for ellipse fitting
                    major_axis = max(w, h)

                # Equivalent diameter (before offset correction)
                equivalent_diameter_raw = np.sqrt(4 * area / np.pi)
                
                # Apply radius offset correction for threshold bias
                # Offset is applied to radius, so diameter = 2 * (radius + offset)
                radius_raw = equivalent_diameter_raw / 2.0
                corrected_radius = max(0.0, radius_raw + radius_offset_px)  # Ensure non-negative
                equivalent_diameter = corrected_radius * 2.0
                
                # Also apply offset to major_axis (treat as diameter)
                major_axis_radius = major_axis / 2.0
                corrected_major_radius = max(0.0, major_axis_radius + radius_offset_px)
                major_axis = corrected_major_radius * 2.0

                metrics.append(
                    DropletMetrics(
                        area=area,
                        major_axis=major_axis,
                        equivalent_diameter=equivalent_diameter,
                        centroid=centroid,
                        bounding_box=(x, y, w, h),
                        aspect_ratio=aspect_ratio,
                    )
                )
            except Exception as e:
                logger.warning(f"Error measuring contour: {e}")
                continue

        return metrics
