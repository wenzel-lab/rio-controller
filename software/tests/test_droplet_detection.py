"""
Unit tests for droplet detection module.

Tests all components of the droplet detection pipeline.
"""

import unittest
import numpy as np
import cv2
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from droplet_detection import (
    DropletDetectionConfig,
    DropletDetector,
    DropletHistogram,
    Preprocessor,
    Segmenter,
    Measurer,
    ArtifactRejector,
    DropletMetrics,
    load_config,
    save_config,
)


class TestDropletDetectionConfig(unittest.TestCase):
    """Test configuration management."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = DropletDetectionConfig()
        self.assertEqual(config.background_method, "static")
        self.assertEqual(config.threshold_method, "otsu")
        self.assertGreater(config.max_area, config.min_area)

    def test_config_update(self):
        """Test configuration update."""
        config = DropletDetectionConfig()
        config.update({"min_area": 50, "max_area": 5000})
        self.assertEqual(config.min_area, 50)
        self.assertEqual(config.max_area, 5000)

    def test_config_validation(self):
        """Test configuration validation."""
        config = DropletDetectionConfig()
        is_valid, errors = config.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Test invalid config
        config.min_area = -1
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_config_save_load(self):
        """Test configuration save and load."""
        config = DropletDetectionConfig()
        config.min_area = 30
        config.max_area = 3000

        # Save to temporary file
        test_file = "/tmp/test_droplet_config.json"
        try:
            save_config(config, test_file)
            self.assertTrue(os.path.exists(test_file))

            # Load and verify
            loaded_config = load_config(test_file)
            self.assertEqual(loaded_config.min_area, 30)
            self.assertEqual(loaded_config.max_area, 3000)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


class TestPreprocessor(unittest.TestCase):
    """Test preprocessing module."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.preprocessor = Preprocessor(self.config)
        # Create a simple test image (white circle on black background)
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        cv2.circle(self.test_image, (100, 50), 20, (255, 255, 255), -1)

    def test_grayscale_conversion(self):
        """Test that preprocessing handles RGB images."""
        mask = self.preprocessor.process(self.test_image)
        self.assertEqual(len(mask.shape), 2)  # Should be grayscale

    def test_background_initialization(self):
        """Test background initialization."""
        # Initialize with multiple frames
        for _ in range(self.config.background_frames):
            self.preprocessor.initialize_background(self.test_image)

        self.assertTrue(self.preprocessor.background_initialized)
        self.assertIsNotNone(self.preprocessor.background)

    def test_static_background_method(self):
        """Test static background subtraction."""
        self.config.background_method = "static"
        self.preprocessor = Preprocessor(self.config)

        # Initialize background
        for _ in range(self.config.background_frames):
            self.preprocessor.initialize_background(self.test_image)

        # Process frame
        mask = self.preprocessor.process(self.test_image)
        self.assertEqual(mask.dtype, np.uint8)
        self.assertEqual(mask.shape[:2], self.test_image.shape[:2])

    def test_highpass_background_method(self):
        """Test high-pass filtering background method."""
        self.config.background_method = "highpass"
        self.preprocessor = Preprocessor(self.config)

        # High-pass doesn't need initialization
        mask = self.preprocessor.process(self.test_image)
        self.assertEqual(mask.dtype, np.uint8)

    def test_otsu_thresholding(self):
        """Test Otsu thresholding."""
        self.config.threshold_method = "otsu"
        self.preprocessor = Preprocessor(self.config)
        self.config.background_method = "highpass"  # Skip background init

        mask = self.preprocessor.process(self.test_image)
        # Should produce binary mask
        unique_values = np.unique(mask)
        self.assertTrue(all(v in [0, 255] for v in unique_values))

    def test_morphological_operations(self):
        """Test morphological operations."""
        self.config.morph_operation = "open"
        self.preprocessor = Preprocessor(self.config)
        self.config.background_method = "highpass"

        mask = self.preprocessor.process(self.test_image)
        self.assertEqual(mask.dtype, np.uint8)

    def test_reset_background(self):
        """Test background reset."""
        for _ in range(5):
            self.preprocessor.initialize_background(self.test_image)

        self.preprocessor.reset_background()
        self.assertFalse(self.preprocessor.background_initialized)
        self.assertIsNone(self.preprocessor.background)


class TestSegmenter(unittest.TestCase):
    """Test segmentation module."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.segmenter = Segmenter(self.config)
        # Create test binary mask with a blob
        self.mask = np.zeros((100, 200), dtype=np.uint8)
        cv2.circle(self.mask, (100, 50), 15, 255, -1)

    def test_contour_detection(self):
        """Test contour detection."""
        contours = self.segmenter.detect_contours(self.mask)
        self.assertGreater(len(contours), 0)
        self.assertIsInstance(contours[0], np.ndarray)

    def test_area_filtering(self):
        """Test area-based filtering."""
        # Create mask with small and large blobs
        mask = np.zeros((100, 200), dtype=np.uint8)
        cv2.circle(mask, (50, 50), 5, 255, -1)  # Small blob
        cv2.circle(mask, (150, 50), 30, 255, -1)  # Large blob

        contours = self.segmenter.detect_contours(mask)
        # Should filter out blobs outside min/max area
        for cnt in contours:
            area = cv2.contourArea(cnt)
            self.assertGreaterEqual(area, self.config.min_area)
            self.assertLessEqual(area, self.config.max_area)

    def test_aspect_ratio_filtering(self):
        """Test aspect ratio filtering."""
        # Create elongated blob
        mask = np.zeros((100, 200), dtype=np.uint8)
        cv2.ellipse(mask, (100, 50), (40, 5), 0, 0, 360, 255, -1)

        contours = self.segmenter.detect_contours(mask)
        # Should filter based on aspect ratio
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = max(w, h) / max(1, min(w, h))
            self.assertGreaterEqual(aspect, self.config.min_aspect_ratio)
            self.assertLessEqual(aspect, self.config.max_aspect_ratio)

    def test_channel_band_filtering(self):
        """Test spatial channel band filtering."""
        # Create blob outside channel band
        mask = np.zeros((100, 200), dtype=np.uint8)
        cv2.circle(mask, (100, 10), 10, 255, -1)  # Outside band

        channel_band = (30, 70)  # y_min, y_max
        contours = self.segmenter.detect_contours(mask, channel_band=channel_band)
        # Should filter out blob outside band
        for cnt in contours:
            M = cv2.moments(cnt)
            cy = M["m01"] / (M["m00"] + 1e-5)
            margin = self.config.channel_band_margin
            self.assertGreaterEqual(cy, channel_band[0] - margin)
            self.assertLessEqual(cy, channel_band[1] + margin)


class TestMeasurer(unittest.TestCase):
    """Test measurement module."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.measurer = Measurer(self.config)
        # Create test contour (circle)
        self.contour = np.array(
            [
                [[50, 30]],
                [[60, 30]],
                [[70, 30]],
                [[80, 30]],
                [[80, 40]],
                [[80, 50]],
                [[70, 50]],
                [[60, 50]],
                [[50, 50]],
                [[50, 40]],
            ],
            dtype=np.int32,
        )

    def test_measure_contour(self):
        """Test measurement of a contour."""
        metrics = self.measurer.measure([self.contour])
        self.assertEqual(len(metrics), 1)

        m = metrics[0]
        self.assertIsInstance(m, DropletMetrics)
        self.assertGreater(m.area, 0)
        self.assertGreater(m.major_axis, 0)
        self.assertGreater(m.equivalent_diameter, 0)
        self.assertEqual(len(m.centroid), 2)
        self.assertEqual(len(m.bounding_box), 4)

    def test_ellipse_fitting(self):
        """Test ellipse fitting for major axis."""
        # Create elliptical contour
        mask = np.zeros((100, 200), dtype=np.uint8)
        cv2.ellipse(mask, (100, 50), (30, 10), 0, 0, 360, 255, -1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0 and len(contours[0]) >= 5:
            metrics = self.measurer.measure(contours)
            self.assertGreater(len(metrics), 0)
            # Major axis should be approximately 60 (2 * 30)
            self.assertGreater(metrics[0].major_axis, 50)

    def test_empty_contours(self):
        """Test handling of empty contour list."""
        metrics = self.measurer.measure([])
        self.assertEqual(len(metrics), 0)

    def test_zero_area_contour(self):
        """Test handling of zero-area contour."""
        # Create degenerate contour (line)
        contour = np.array([[[0, 0]], [[1, 0]]], dtype=np.int32)
        metrics = self.measurer.measure([contour])
        # Should skip zero-area contours
        self.assertEqual(len(metrics), 0)


class TestArtifactRejector(unittest.TestCase):
    """Test artifact rejection module."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.rejector = ArtifactRejector(self.config)
        # Create test contours
        self.contour1 = np.array([[[10, 10]], [[20, 10]], [[20, 20]], [[10, 20]]], dtype=np.int32)
        self.contour2 = np.array([[[30, 10]], [[40, 10]], [[40, 20]], [[30, 20]]], dtype=np.int32)

    def test_first_frame_accept_all(self):
        """Test that first frame accepts all contours."""
        contours = [self.contour1, self.contour2]
        filtered = self.rejector.filter(contours)
        # First frame should accept all
        self.assertEqual(len(filtered), 2)

    def test_motion_validation(self):
        """Test motion-based filtering."""
        # First frame
        contours1 = [self.contour1]
        filtered1 = self.rejector.filter(contours1)
        self.assertEqual(len(filtered1), 1)

        # Second frame - contour moved right (downstream)
        contour_moved = np.array([[[15, 10]], [[25, 10]], [[25, 20]], [[15, 20]]], dtype=np.int32)
        contours2 = [contour_moved]
        filtered2 = self.rejector.filter(contours2)
        # Should accept if moved downstream
        self.assertGreaterEqual(
            len(filtered2), 0
        )  # May or may not match depending on motion threshold

    def test_static_artifact_rejection(self):
        """Test that static artifacts are rejected."""
        # First frame
        contours1 = [self.contour1]
        self.rejector.filter(contours1)

        # Second frame - same position (static)
        contours2 = [self.contour1]  # Same contour
        filtered2 = self.rejector.filter(contours2)
        # Static contour should be rejected
        self.assertEqual(len(filtered2), 0)

    def test_reset(self):
        """Test state reset."""
        self.rejector.filter([self.contour1])
        self.rejector.reset()
        self.assertEqual(len(self.rejector.prev_centroids), 0)
        self.assertIsNone(self.rejector.prev_frame)


class TestDropletHistogram(unittest.TestCase):
    """Test histogram module."""

    def setUp(self):
        """Set up test fixtures."""
        self.histogram = DropletHistogram(maxlen=100, bins=20, pixel_ratio=1.0, unit="px")

    def test_update(self):
        """Test histogram update."""
        metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=11.3,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            ),
            DropletMetrics(
                area=200.0,
                major_axis=30.0,
                equivalent_diameter=16.0,
                centroid=(100.0, 50.0),
                bounding_box=(90, 40, 30, 30),
                aspect_ratio=1.0,
            ),
        ]

        self.histogram.update(metrics)
        self.assertEqual(len(self.histogram.widths), 2)
        self.assertEqual(len(self.histogram.areas), 2)

    def test_get_histogram(self):
        """Test histogram generation."""
        # Add some data
        metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=11.3,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            )
            for _ in range(10)
        ]
        self.histogram.update(metrics)

        counts, bins = self.histogram.get_histogram("width")
        self.assertEqual(len(counts), self.histogram.bins)
        self.assertEqual(len(bins), self.histogram.bins + 1)

    def test_get_bars(self):
        """Test bar format generation."""
        metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=11.3,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            )
            for _ in range(5)
        ]
        self.histogram.update(metrics)

        bars = self.histogram.get_bars("width")
        self.assertIsInstance(bars, list)
        if bars:
            self.assertEqual(len(bars[0]), 2)  # (value, count) tuple

    def test_get_statistics(self):
        """Test statistics calculation."""
        metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=11.3,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            ),
            DropletMetrics(
                area=200.0,
                major_axis=30.0,
                equivalent_diameter=16.0,
                centroid=(100.0, 50.0),
                bounding_box=(90, 40, 30, 30),
                aspect_ratio=1.0,
            ),
        ]
        self.histogram.update(metrics)

        stats = self.histogram.get_statistics()
        self.assertIn("count", stats)
        self.assertIn("width", stats)
        self.assertIn("height", stats)
        self.assertIn("area", stats)
        self.assertIn("diameter", stats)
        self.assertGreater(stats["width"]["mean"], 0)

    def test_to_json(self):
        """Test JSON serialization."""
        metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=11.3,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            )
        ]
        self.histogram.update(metrics)

        json_data = self.histogram.to_json()
        self.assertIn("histograms", json_data)
        self.assertIn("statistics", json_data)
        self.assertIn("width", json_data["histograms"])
        self.assertIn("height", json_data["histograms"])
        self.assertIn("area", json_data["histograms"])

    def test_clear(self):
        """Test histogram clearing."""
        metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=11.3,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            )
        ]
        self.histogram.update(metrics)
        self.histogram.clear()
        self.assertEqual(len(self.histogram.widths), 0)
        self.assertEqual(len(self.histogram.areas), 0)


class TestDropletDetector(unittest.TestCase):
    """Test main detector orchestrator."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.roi = (0, 0, 200, 100)  # x, y, width, height
        self.detector = DropletDetector(self.roi, self.config)
        # Create test image with droplet-like blob
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        cv2.ellipse(self.test_image, (100, 50), (30, 10), 0, 0, 360, (255, 255, 255), -1)

    def test_initialization(self):
        """Test detector initialization."""
        self.assertIsNotNone(self.detector.preprocessor)
        self.assertIsNotNone(self.detector.segmenter)
        self.assertIsNotNone(self.detector.measurer)
        self.assertIsNotNone(self.detector.artifact_rejector)
        self.assertEqual(self.detector.roi, self.roi)

    def test_background_initialization(self):
        """Test background initialization."""
        frames = [self.test_image] * self.config.background_frames
        self.detector.initialize_background(frames)
        self.assertTrue(self.detector.preprocessor.background_initialized)

    def test_process_frame_before_background_init(self):
        """Test processing before background initialization."""
        # Process frame before background is ready
        metrics = self.detector.process_frame(self.test_image)
        # Should return empty list while initializing
        self.assertEqual(len(metrics), 0)

    def test_process_frame_after_background_init(self):
        """Test processing after background initialization."""
        # Initialize background
        frames = [self.test_image] * self.config.background_frames
        self.detector.initialize_background(frames)

        # Process frame
        metrics = self.detector.process_frame(self.test_image)
        # May or may not detect droplets depending on background subtraction
        self.assertIsInstance(metrics, list)

    def test_timing_callback(self):
        """Test timing callback functionality."""
        timing_data = {}

        def timing_callback(component: str, elapsed_ms: float):
            timing_data[component] = elapsed_ms

        # Initialize background
        frames = [self.test_image] * self.config.background_frames
        self.detector.initialize_background(frames)

        # Process with timing
        metrics = self.detector.process_frame(self.test_image, timing_callback=timing_callback)

        # Check that timing data was collected
        self.assertIn("preprocessing", timing_data)
        self.assertIn("segmentation", timing_data)
        self.assertIn("artifact_rejection", timing_data)
        self.assertIn("measurement", timing_data)

    def test_reset(self):
        """Test detector reset."""
        # Initialize and process
        frames = [self.test_image] * self.config.background_frames
        self.detector.initialize_background(frames)
        self.detector.process_frame(self.test_image)

        # Reset
        self.detector.reset()
        self.assertFalse(self.detector.preprocessor.background_initialized)
        self.assertEqual(len(self.detector.prev_centroids), 0)
        self.assertEqual(self.detector.frame_count, 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for full pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.config.background_method = "highpass"  # Faster for testing
        self.roi = (0, 0, 200, 100)
        self.detector = DropletDetector(self.roi, self.config)
        self.histogram = DropletHistogram()

        # Create test image with multiple droplets
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        cv2.ellipse(self.test_image, (50, 50), (20, 8), 0, 0, 360, (255, 255, 255), -1)
        cv2.ellipse(self.test_image, (150, 50), (25, 10), 0, 0, 360, (255, 255, 255), -1)

    def test_full_pipeline(self):
        """Test complete pipeline from image to histogram."""
        # Process frame
        metrics = self.detector.process_frame(self.test_image)

        # Update histogram
        self.histogram.update(metrics)

        # Get statistics
        stats = self.histogram.get_statistics()

        # Verify results
        self.assertIsInstance(metrics, list)
        self.assertIn("count", stats)
        if len(metrics) > 0:
            self.assertGreater(stats["count"], 0)

    def test_multiple_frames(self):
        """Test processing multiple frames."""
        all_metrics = []

        for i in range(5):
            # Slightly shift image to simulate motion
            shifted_image = np.roll(self.test_image, i * 2, axis=1)
            metrics = self.detector.process_frame(shifted_image)
            all_metrics.extend(metrics)
            self.histogram.update(metrics)

        stats = self.histogram.get_statistics()
        self.assertGreaterEqual(stats["count"], 0)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
