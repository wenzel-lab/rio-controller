"""
Histogram and statistics module for droplet detection.

Implements sliding-window histogram and real-time statistics.
Based on structure from droplet_AInalysis repository.
"""

import logging
import numpy as np
from typing import Dict, Optional, Tuple, List
from collections import deque

from .measurer import DropletMetrics

logger = logging.getLogger(__name__)


class DropletHistogram:
    """
    Histogram and statistics module for droplet detection.

    Implements:
    - Sliding-window histogram (deque with maxlen)
    - Real-time statistics (mean, std, min, max, count, mode)
    - Width, Height, and Area distributions (matching AInalysis structure)
    - JSON serialization

    Based on ImageData structure from droplet_AInalysis repository.
    """

    def __init__(
        self, maxlen: int = 2000, bins: int = 40, pixel_ratio: float = 1.0, unit: str = "px"
    ):
        """
        Initialize histogram.

        Args:
            maxlen: Maximum number of measurements to store (sliding window)
            bins: Number of bins for histogram
            pixel_ratio: Conversion factor from pixels to physical units
            unit: Unit string (e.g., "px", "μm", "mm")
        """
        self.maxlen = maxlen
        self.bins = bins
        self.pixel_ratio = pixel_ratio
        self.unit = unit

        # Store measurements in deques (sliding window)
        # Width = major axis (droplet length)
        # Height = minor axis (from ellipse or bounding box)
        # Diameter = equivalent diameter
        # Area = contour area
        self.widths = deque(maxlen=maxlen)  # Major axis (length)
        self.heights = deque(maxlen=maxlen)  # Minor axis
        self.diameters = deque(maxlen=maxlen)  # Equivalent diameter
        self.areas = deque(maxlen=maxlen)  # Contour area

    def update(self, metrics: List[DropletMetrics]) -> None:
        """
        Update histogram with new droplet measurements.

        Args:
            metrics: List of DropletMetrics objects
        """
        if not metrics:
            return  # Skip empty lists

        for m in metrics:
            # Width = major axis (droplet length)
            self.widths.append(m.major_axis)
            # Height = minor axis (from bounding box or ellipse)
            # Use bounding box height as approximation
            _, _, w, h = m.bounding_box
            minor_axis = min(w, h)
            self.heights.append(minor_axis)
            # Diameter = equivalent diameter
            self.diameters.append(m.equivalent_diameter)
            # Area = contour area
            self.areas.append(m.area)

    def get_histogram(
        self, metric: str = "width", range: Optional[Tuple[float, float]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get histogram data.

        Args:
            metric: Metric to histogram ("width", "height", "diameter", or "area")
            range: Optional (min, max) range for histogram bins

        Returns:
            Tuple of (counts, bin_edges)
        """
        # Get appropriate deque
        if metric == "width":
            data_deque = self.widths
        elif metric == "height":
            data_deque = self.heights
        elif metric == "diameter":
            data_deque = self.diameters
        elif metric == "area":
            data_deque = self.areas
        else:
            raise ValueError(
                f"Unknown metric: {metric}. Use 'width', 'height', 'diameter', or 'area'"
            )

        if not data_deque:
            # Return empty histogram
            if range:
                bins_array = np.linspace(range[0], range[1], self.bins + 1)
            else:
                bins_array = np.linspace(0, 100, self.bins + 1)
            return np.zeros(self.bins, dtype=np.int64), bins_array

        # Convert deque to numpy array directly (more efficient than list() then array())
        data = np.array(data_deque, dtype=np.float64)  # Use float64 for histogram input
        return np.histogram(data, bins=self.bins, range=range)

    def get_bars(self, metric: str = "width") -> List[Tuple[float, int]]:
        """
        Get histogram bars in format matching AInalysis structure.

        Returns sorted list of [(value, count), ...] pairs.
        This format is useful for grouping and interval operations.

        Optimized using numpy operations for better performance.

        Args:
            metric: Metric to get bars for ("width", "height", "diameter", or "area")

        Returns:
            List of (value, count) tuples, sorted by value
        """
        # Get appropriate deque
        if metric == "width":
            data_deque = self.widths
        elif metric == "height":
            data_deque = self.heights
        elif metric == "diameter":
            data_deque = self.diameters
        elif metric == "area":
            data_deque = self.areas
        else:
            raise ValueError(f"Unknown metric: {metric}")

        if not data_deque:
            return []

        # Convert deque to numpy array directly (more efficient)
        # Use float32 for memory efficiency on Raspberry Pi
        data_array = np.array(data_deque, dtype=np.float32)
        data_int = np.round(data_array).astype(np.int32)

        if data_int.size == 0:
            return []

        # Use numpy.bincount for efficient counting (optimized for Raspberry Pi)
        min_val = int(data_int.min())
        if min_val < 0:
            data_int = data_int - min_val

        counts = np.bincount(data_int)

        # Build result list (only non-zero counts) - use list comprehension for efficiency
        bars = [
            (float(idx + min_val if min_val < 0 else idx), int(count))
            for idx, count in enumerate(counts)
            if count > 0
        ]

        # Sort by value (should already be sorted, but ensure it)
        bars.sort(key=lambda x: x[0])

        return bars

    def get_statistics(self) -> Dict:
        """
        Get real-time statistics matching AInalysis structure.

        Optimized to use vectorized numpy operations for better performance.

        Returns:
            Dictionary of statistics with width, height, diameter, and area metrics
        """
        stats = {
            "count": int(len(self.widths)),  # Total number of droplets (integer)
            "unit": self.unit,
            "pixel_ratio": self.pixel_ratio,
        }

        # Helper function to compute statistics efficiently
        def _compute_stats(data: deque, ratio: float) -> Dict[str, int]:
            """Compute statistics for a metric using vectorized operations."""
            if not data:
                return {"mean": 0, "std": 0, "min": 0, "max": 0, "mode": 0}

            # Convert to numpy array once (more efficient than multiple list() calls)
            data_array = np.array(data, dtype=np.float32)
            scaled = data_array * ratio

            return {
                "mean": int(round(np.mean(scaled))),
                "std": int(round(np.std(scaled))),
                "min": int(round(np.min(scaled))),
                "max": int(round(np.max(scaled))),
                "mode": int(round(self._get_mode(data))),
            }

        # Width statistics (major axis) - rounded to integers in um
        stats["width"] = _compute_stats(self.widths, self.pixel_ratio)

        # Height statistics (minor axis) - rounded to integers in um
        stats["height"] = _compute_stats(self.heights, self.pixel_ratio)

        # Diameter statistics - rounded to integers in um
        stats["diameter"] = _compute_stats(self.diameters, self.pixel_ratio)

        # Area statistics (note: area uses pixel_ratio²) - rounded to integers
        area_ratio = self.pixel_ratio**2
        stats["area"] = _compute_stats(self.areas, area_ratio)

        return stats

    def _get_mode(self, data: deque) -> float:
        """
        Calculate mode (most frequent value) from data.

        Optimized using numpy.bincount for better performance on Raspberry Pi.

        Args:
            data: Deque of values

        Returns:
            Mode value in physical units
        """
        if not data:
            return 0.0

        # Convert deque to numpy array directly (more efficient than list() then array())
        # Use float32 for memory efficiency on Raspberry Pi
        data_array = np.array(data, dtype=np.float32)
        rounded = np.round(data_array).astype(np.int32)

        # Use numpy.bincount for efficient counting (faster than dict on large datasets)
        # This is optimized for Raspberry Pi (works on both 32-bit and 64-bit)
        if rounded.size == 0:
            return 0.0

        # Handle negative values by shifting (bincount requires non-negative)
        min_val = int(rounded.min())
        if min_val < 0:
            rounded = rounded - min_val

        counts = np.bincount(rounded)
        if counts.size == 0:
            return 0.0

        mode_idx = int(np.argmax(counts))
        mode_value = mode_idx + min_val if min_val < 0 else mode_idx

        # Return mode in physical units (will be rounded in get_statistics)
        return float(mode_value * self.pixel_ratio)

    def to_json(self) -> Dict:
        """
        Serialize to JSON for API.

        Returns:
            Dictionary with histograms and statistics for all metrics
        """
        hist_width, bins_width = self.get_histogram("width")
        hist_height, bins_height = self.get_histogram("height")
        hist_area, bins_area = self.get_histogram("area")
        hist_diameter, bins_diameter = self.get_histogram("diameter")

        return {
            "histograms": {
                "width": {
                    "counts": hist_width.astype(
                        np.int32
                    ).tolist(),  # Integer counts (more efficient)
                    "bins": bins_width.tolist(),
                    "bars": self.get_bars("width"),  # For compatibility with AInalysis format
                },
                "height": {
                    "counts": hist_height.astype(
                        np.int32
                    ).tolist(),  # Integer counts (more efficient)
                    "bins": bins_height.tolist(),
                    "bars": self.get_bars("height"),
                },
                "area": {
                    "counts": hist_area.astype(
                        np.int32
                    ).tolist(),  # Integer counts (more efficient)
                    "bins": bins_area.tolist(),
                    "bars": self.get_bars("area"),
                },
                "diameter": {
                    "counts": hist_diameter.astype(
                        np.int32
                    ).tolist(),  # Integer counts (more efficient)
                    "bins": bins_diameter.tolist(),
                    "bars": self.get_bars("diameter"),
                },
            },
            "statistics": self.get_statistics(),
            "pixel_ratio": self.pixel_ratio,  # Include pixel ratio for unit conversion
            "unit": self.unit,  # Include unit (um or px)
            "count": int(len(self.widths)),  # Total count as integer
        }

    def clear(self) -> None:
        """Clear all stored measurements."""
        self.widths.clear()
        self.heights.clear()
        self.diameters.clear()
        self.areas.clear()
        logger.debug("Histogram cleared")
