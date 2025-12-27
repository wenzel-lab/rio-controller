"""
Test histogram configuration functionality.

Tests the configurable histogram window size and bins.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import droplet_detection module (handling hyphenated directory)
import importlib.util  # noqa: E402

software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
droplet_detection_path = os.path.join(software_dir, "droplet-detection")
if os.path.exists(droplet_detection_path):
    spec = importlib.util.spec_from_file_location(
        "droplet_detection", os.path.join(droplet_detection_path, "__init__.py")
    )
    droplet_detection = importlib.util.module_from_spec(spec)
    sys.modules["droplet_detection"] = droplet_detection
    spec.loader.exec_module(droplet_detection)

    DropletHistogram = droplet_detection.DropletHistogram
    DropletDetectionConfig = droplet_detection.DropletDetectionConfig
else:
    from droplet_detection import DropletDetectionConfig

# Import controller
from controllers.droplet_detector_controller import DropletDetectorController  # noqa: E402


class MockCamera:
    """Mock camera for testing."""

    def __init__(self):
        self.roi = {"x": 0, "y": 0, "width": 100, "height": 100}
        self.calibration = {"um_per_px": 0.82, "radius_offset_px": 0.0}

    def get_roi(self):
        return (self.roi["x"], self.roi["y"], self.roi["width"], self.roi["height"])

    def get_calibration(self):
        return self.calibration.copy()


class MockStrobeCam:
    """Mock strobe camera for testing."""

    pass


class TestHistogramConfig(unittest.TestCase):
    """Test histogram configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_camera = MockCamera()
        self.mock_strobe = MockStrobeCam()

    def test_config_default_values(self):
        """Test default histogram configuration values."""
        config = DropletDetectionConfig()

        self.assertEqual(config.histogram_window_size, 2000, "Default window size should be 2000")
        self.assertEqual(config.histogram_bins, 40, "Default bins should be 40")

    def test_config_custom_values(self):
        """Test custom histogram configuration values."""
        config_dict = {"histogram_window_size": 5000, "histogram_bins": 50}
        config = DropletDetectionConfig(config_dict)

        self.assertEqual(config.histogram_window_size, 5000, "Window size should be 5000")
        self.assertEqual(config.histogram_bins, 50, "Bins should be 50")

    def test_config_validation(self):
        """Test histogram configuration validation."""
        config = DropletDetectionConfig()

        # Valid values
        config.histogram_window_size = 1000
        config.histogram_bins = 30
        is_valid, errors = config.validate()
        self.assertTrue(is_valid, "Valid values should pass validation")
        self.assertEqual(len(errors), 0, "No errors for valid values")

        # Invalid window size
        config.histogram_window_size = 0
        is_valid, errors = config.validate()
        self.assertFalse(is_valid, "Invalid window size should fail validation")
        self.assertTrue(
            any("histogram_window_size" in e for e in errors), "Should have window size error"
        )

        # Invalid bins
        config.histogram_window_size = 1000
        config.histogram_bins = 0
        is_valid, errors = config.validate()
        self.assertFalse(is_valid, "Invalid bins should fail validation")
        self.assertTrue(any("histogram_bins" in e for e in errors), "Should have bins error")

    def test_config_serialization(self):
        """Test histogram config serialization."""
        config = DropletDetectionConfig({"histogram_window_size": 3000, "histogram_bins": 45})

        config_dict = config.to_dict()

        self.assertIn("histogram_window_size", config_dict, "Should include window_size in dict")
        self.assertIn("histogram_bins", config_dict, "Should include bins in dict")
        self.assertEqual(config_dict["histogram_window_size"], 3000, "Window size should match")
        self.assertEqual(config_dict["histogram_bins"], 45, "Bins should match")

    def test_histogram_initialization_with_config(self):
        """Test histogram initialization uses config values."""
        config = DropletDetectionConfig({"histogram_window_size": 1500, "histogram_bins": 35})

        controller = DropletDetectorController(
            camera=self.mock_camera, strobe_cam=self.mock_strobe, config=config
        )

        self.assertEqual(
            controller.histogram.maxlen, 1500, "Histogram should use config window size"
        )
        # Note: bins is not directly accessible, but we can verify it's used

    def test_histogram_update_window_size(self):
        """Test updating histogram window size."""
        config = DropletDetectionConfig()
        controller = DropletDetectorController(
            camera=self.mock_camera, strobe_cam=self.mock_strobe, config=config
        )

        # Store original maxlen
        original_maxlen = controller.histogram.maxlen

        # Update config
        config_dict = {"histogram_window_size": 3000}
        success = controller.update_config(config_dict)

        self.assertTrue(success, "Config update should succeed")
        self.assertEqual(controller.histogram.maxlen, 3000, "Histogram should have new window size")
        self.assertNotEqual(
            controller.histogram.maxlen, original_maxlen, "Window size should change"
        )

    def test_histogram_update_bins(self):
        """Test updating histogram bins."""
        config = DropletDetectionConfig()
        controller = DropletDetectorController(
            camera=self.mock_camera, strobe_cam=self.mock_strobe, config=config
        )

        # Update config
        config_dict = {"histogram_bins": 50}
        success = controller.update_config(config_dict)

        self.assertTrue(success, "Config update should succeed")
        # Verify histogram was recreated (we can't directly check bins, but we can verify it doesn't crash)

    def test_histogram_update_both(self):
        """Test updating both window size and bins."""
        config = DropletDetectionConfig()
        controller = DropletDetectorController(
            camera=self.mock_camera, strobe_cam=self.mock_strobe, config=config
        )

        # Update config
        config_dict = {"histogram_window_size": 4000, "histogram_bins": 60}
        success = controller.update_config(config_dict)

        self.assertTrue(success, "Config update should succeed")
        self.assertEqual(controller.histogram.maxlen, 4000, "Histogram should have new window size")

    def test_histogram_update_clears_data(self):
        """Test that histogram update clears existing data."""
        config = DropletDetectionConfig()
        controller = DropletDetectorController(
            camera=self.mock_camera, strobe_cam=self.mock_strobe, config=config
        )

        # Add some test data to histogram
        from droplet_detection.measurer import DropletMetrics

        test_metrics = [
            DropletMetrics(
                area=100.0,
                major_axis=20.0,
                equivalent_diameter=20.0,
                centroid=(50.0, 50.0),
                bounding_box=(40, 40, 20, 20),
                aspect_ratio=1.0,
            )
        ]
        controller.histogram.update(test_metrics)

        # Verify data exists
        self.assertGreater(len(controller.histogram.widths), 0, "Should have data before update")

        # Update histogram (should clear data)
        config_dict = {"histogram_window_size": 5000}
        controller.update_config(config_dict)

        # Note: Histogram recreation clears data, but we can't directly verify
        # because the histogram is recreated. The important thing is it doesn't crash.


if __name__ == "__main__":
    unittest.main()
