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
        if metric == "width":
            data = list(self.widths)
        elif metric == "height":
            data = list(self.heights)
        elif metric == "diameter":
            data = list(self.diameters)
        elif metric == "area":
            data = list(self.areas)
        else:
            raise ValueError(
                f"Unknown metric: {metric}. Use 'width', 'height', 'diameter', or 'area'"
            )

        if not data:
            # Return empty histogram
            if range:
                bins_array = np.linspace(range[0], range[1], self.bins + 1)
            else:
                bins_array = np.linspace(0, 100, self.bins + 1)
            return np.zeros(self.bins, dtype=np.int64), bins_array

        return np.histogram(data, bins=self.bins, range=range)

    def get_bars(self, metric: str = "width") -> List[Tuple[float, int]]:
        """
        Get histogram bars in format matching AInalysis structure.

        Returns sorted list of [(value, count), ...] pairs.
        This format is useful for grouping and interval operations.

        Args:
            metric: Metric to get bars for ("width", "height", "diameter", or "area")

        Returns:
            List of (value, count) tuples, sorted by value
        """
        if metric == "width":
            data = list(self.widths)
        elif metric == "height":
            data = list(self.heights)
        elif metric == "diameter":
            data = list(self.diameters)
        elif metric == "area":
            data = list(self.areas)
        else:
            raise ValueError(f"Unknown metric: {metric}")

        if not data:
            return []

        # Sort and group (similar to sort_and_group in AInalysis)
        data_sorted = sorted([int(d) for d in data])
        if not data_sorted:
            return []

        bars = []
        current_value = data_sorted[0]
        count = 1

        for value in data_sorted[1:]:
            if value == current_value:
                count += 1
            else:
                bars.append((float(current_value), count))
                current_value = value
                count = 1
        bars.append((float(current_value), count))

        return bars

    def get_statistics(self) -> Dict:
        """
        Get real-time statistics matching AInalysis structure.

        Returns:
            Dictionary of statistics with width, height, diameter, and area metrics
        """
        stats = {
            "count": int(len(self.widths)),  # Total number of droplets (integer)
            "unit": self.unit,
            "pixel_ratio": self.pixel_ratio,
        }

        # Width statistics (major axis) - rounded to integers in um
        if self.widths:
            stats["width"] = {
                "mean": int(round(np.mean(self.widths) * self.pixel_ratio)),
                "std": int(round(np.std(self.widths) * self.pixel_ratio)),
                "min": int(round(np.min(self.widths) * self.pixel_ratio)),
                "max": int(round(np.max(self.widths) * self.pixel_ratio)),
                "mode": int(round(self._get_mode(self.widths))),
            }
        else:
            stats["width"] = {"mean": 0, "std": 0, "min": 0, "max": 0, "mode": 0}

        # Height statistics (minor axis) - rounded to integers in um
        if self.heights:
            stats["height"] = {
                "mean": int(round(np.mean(self.heights) * self.pixel_ratio)),
                "std": int(round(np.std(self.heights) * self.pixel_ratio)),
                "min": int(round(np.min(self.heights) * self.pixel_ratio)),
                "max": int(round(np.max(self.heights) * self.pixel_ratio)),
                "mode": int(round(self._get_mode(self.heights))),
            }
        else:
            stats["height"] = {"mean": 0, "std": 0, "min": 0, "max": 0, "mode": 0}

        # Diameter statistics - rounded to integers in um
        if self.diameters:
            stats["diameter"] = {
                "mean": int(round(np.mean(self.diameters) * self.pixel_ratio)),
                "std": int(round(np.std(self.diameters) * self.pixel_ratio)),
                "min": int(round(np.min(self.diameters) * self.pixel_ratio)),
                "max": int(round(np.max(self.diameters) * self.pixel_ratio)),
                "mode": int(round(self._get_mode(self.diameters))),
            }
        else:
            stats["diameter"] = {"mean": 0, "std": 0, "min": 0, "max": 0, "mode": 0}

        # Area statistics (note: area uses pixel_ratio²) - rounded to integers
        if self.areas:
            area_ratio = self.pixel_ratio**2
            stats["area"] = {
                "mean": int(round(np.mean(self.areas) * area_ratio)),
                "std": int(round(np.std(self.areas) * area_ratio)),
                "min": int(round(np.min(self.areas) * area_ratio)),
                "max": int(round(np.max(self.areas) * area_ratio)),
                "mode": int(round(self._get_mode(self.areas))),
            }
        else:
            stats["area"] = {"mean": 0, "std": 0, "min": 0, "max": 0, "mode": 0}

        return stats

    def _get_mode(self, data: deque) -> float:
        """
        Calculate mode (most frequent value) from data.

        Args:
            data: Deque of values

        Returns:
            Mode value in physical units
        """
        if not data:
            return 0.0

        # Round to integers for mode calculation
        rounded = [int(d) for d in data]
        counts = {}
        for value in rounded:
            counts[value] = counts.get(value, 0) + 1

        if not counts:
            return 0.0

        mode_value = max(counts, key=counts.get)
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
                    "counts": [int(c) for c in hist_width.tolist()],  # Integer counts
                    "bins": bins_width.tolist(),
                    "bars": self.get_bars("width"),  # For compatibility with AInalysis format
                },
                "height": {
                    "counts": [int(c) for c in hist_height.tolist()],  # Integer counts
                    "bins": bins_height.tolist(),
                    "bars": self.get_bars("height"),
                },
                "area": {
                    "counts": [int(c) for c in hist_area.tolist()],  # Integer counts
                    "bins": bins_area.tolist(),
                    "bars": self.get_bars("area"),
                },
                "diameter": {
                    "counts": [int(c) for c in hist_diameter.tolist()],  # Integer counts
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
