"""
Artifact rejection module for droplet detection.

Implements temporal filtering and motion validation to reject static artifacts.
"""

import logging
import numpy as np
import cv2
from typing import List, Tuple, Optional

from .config import DropletDetectionConfig
from .utils import get_contour_centroid

# Performance optimization: Use numpy for vectorized operations

logger = logging.getLogger(__name__)


class ArtifactRejector:
    """
    Artifact rejection module for droplet detection.

    Implements:
    - Centroid-based tracking
    - Monotonic downstream motion validation
    - Static artifact rejection
    - Frame difference method (optional)
    """

    def __init__(self, config: DropletDetectionConfig):
        """
        Initialize artifact rejector with configuration.

        Args:
            config: DropletDetectionConfig instance
        """
        self.config = config
        self.prev_centroids: List[Tuple[float, float]] = []
        self.prev_frame: Optional[np.ndarray] = None

    def filter(
        self, contours: List[np.ndarray], prev_centroids: Optional[List[Tuple[float, float]]] = None
    ) -> List[np.ndarray]:
        """
        Filter contours by motion validation.

        Rejects static artifacts by checking if centroids have moved
        downstream (monotonic motion in flow direction).

        Args:
            contours: List of contours to filter
            prev_centroids: Previous frame centroids (if None, uses internal state)

        Returns:
            List of filtered contours (moving droplets)
        """
        if prev_centroids is not None:
            self.prev_centroids = prev_centroids

        # First frame: accept all (no previous frame to compare)
        if not self.prev_centroids:
            # Update state for next frame
            try:
                self.prev_centroids = [get_contour_centroid(cnt) for cnt in contours]
            except Exception as e:
                logger.warning(f"Error calculating centroids: {e}")
                self.prev_centroids = []
            return contours

        moving_contours = []

        # Pre-calculate all centroids (more efficient than calculating in loop)
        centroids = [get_contour_centroid(cnt) for cnt in contours]
        current_centroids = centroids

        # Optimize: Use numpy for vectorized distance calculations if many centroids
        if len(self.prev_centroids) > 0 and len(centroids) > 0:
            # Convert to numpy arrays for vectorized operations
            prev_array = np.array(self.prev_centroids, dtype=np.float32)
            curr_array = np.array(centroids, dtype=np.float32)

            for i, (cnt, centroid) in enumerate(zip(contours, centroids)):
                # Check if this centroid moved downstream
                is_moving = False
                is_new = True  # Assume new droplet until proven otherwise

                # Vectorized calculation: compute all distances at once
                dx = curr_array[i, 0] - prev_array[:, 0]  # x-direction (flow direction)
                dy = np.abs(curr_array[i, 1] - prev_array[:, 1])  # y-direction (perpendicular)

                # Check if any previous centroid matches motion criteria
                motion_mask = (dx > self.config.min_motion) & (dy < self.config.max_perp_drift)
                if np.any(motion_mask):
                    is_moving = True
                    is_new = False
                else:
                    # Check if it's close to a previous centroid (same droplet, not moving enough)
                    close_mask = (np.abs(dx) < self.config.max_perp_drift * 2) & (
                        dy < self.config.max_perp_drift * 2
                    )
                    if np.any(close_mask):
                        is_new = False  # It's a tracked droplet, just not moving enough

                # Accept if moving OR if it's a new droplet entering the frame
                if is_moving or is_new:
                    moving_contours.append(cnt)
        else:
            # First frame or no previous centroids: accept all
            moving_contours = contours

        # Update state for next frame
        self.prev_centroids = current_centroids

        return moving_contours

    def filter_with_frame_diff(
        self,
        contours: List[np.ndarray],
        current_frame: np.ndarray,
        prev_frame: Optional[np.ndarray] = None,
    ) -> List[np.ndarray]:
        """
        Filter contours using frame difference method.

        Only keeps contours in regions that changed significantly
        between frames (rejects static artifacts).

        Args:
            contours: List of contours to filter
            current_frame: Current frame (grayscale)
            prev_frame: Previous frame (grayscale, if None uses internal state)

        Returns:
            List of filtered contours
        """
        if not self.config.use_frame_diff:
            return self.filter(contours)

        if prev_frame is None:
            prev_frame = self.prev_frame

        if prev_frame is None:
            # First frame: accept all
            self.prev_frame = current_frame.copy()
            return contours

        # Compute frame difference
        frame_diff = cv2.absdiff(current_frame, prev_frame)
        _, diff_mask = cv2.threshold(
            frame_diff, self.config.frame_diff_threshold, 255, cv2.THRESH_BINARY
        )

        # Filter contours: only keep those in changed regions
        filtered = []
        for cnt in contours:
            # Check if contour overlaps with changed regions
            # Simple check: see if centroid is in changed region
            centroid = get_contour_centroid(cnt)
            cx, cy = int(centroid[0]), int(centroid[1])

            if (
                0 <= cy < diff_mask.shape[0]
                and 0 <= cx < diff_mask.shape[1]
                and diff_mask[cy, cx] > 0
            ):
                filtered.append(cnt)

        # Update previous frame
        self.prev_frame = current_frame.copy()

        return filtered

    def reset(self) -> None:
        """Reset internal state (for re-initialization)."""
        self.prev_centroids = []
        self.prev_frame = None
        logger.debug("Artifact rejector state reset")
