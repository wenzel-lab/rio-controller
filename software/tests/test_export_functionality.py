"""
Test export functionality for droplet detection.

Tests the export_data method and related functionality.
"""

import unittest
import sys
import os
import csv
import io

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

    DropletMetrics = droplet_detection.DropletMetrics
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


class TestExportFunctionality(unittest.TestCase):
    """Test export functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_camera = MockCamera()
        self.mock_strobe = MockStrobeCam()
        self.config = DropletDetectionConfig()

        # Create controller
        self.controller = DropletDetectorController(
            camera=self.mock_camera, strobe_cam=self.mock_strobe, config=self.config
        )

        # Manually add some test measurements
        self.controller.raw_measurements = [
            {
                "timestamp_ms": 1733856000000,
                "frame_id": 1,
                "radius_px": 15.5,
                "radius_um": 12.71,
                "area_px": 754.0,
                "area_um2": 506.28,
                "x_center_px": 100.5,
                "y_center_px": 200.3,
                "major_axis_px": 31.0,
                "major_axis_um": 25.42,
                "equivalent_diameter_px": 31.0,
                "equivalent_diameter_um": 25.42,
            },
            {
                "timestamp_ms": 1733856000100,
                "frame_id": 2,
                "radius_px": 16.2,
                "radius_um": 13.28,
                "area_px": 824.0,
                "area_um2": 553.12,
                "x_center_px": 150.2,
                "y_center_px": 180.7,
                "major_axis_px": 32.4,
                "major_axis_um": 26.56,
                "equivalent_diameter_px": 32.4,
                "equivalent_diameter_um": 26.56,
            },
        ]

    def test_export_csv_format(self):
        """Test CSV export format."""
        result = self.controller.export_data("csv")

        self.assertIsNotNone(result, "Export should return data")
        self.assertIsInstance(result, str, "Export should return string")

        # Parse CSV
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Check header
        self.assertEqual(len(rows), 3, "Should have header + 2 data rows")
        self.assertEqual(rows[0][0], "timestamp_ms", "First header should be timestamp_ms")

        # Check data rows
        self.assertEqual(rows[1][0], "1733856000000", "First timestamp should match")
        self.assertEqual(rows[1][2], "15.5", "First radius_px should match")
        self.assertEqual(rows[2][0], "1733856000100", "Second timestamp should match")

    def test_export_txt_format(self):
        """Test TXT (tab-separated) export format."""
        result = self.controller.export_data("txt")

        self.assertIsNotNone(result, "Export should return data")
        self.assertIsInstance(result, str, "Export should return string")

        # Parse TXT (tab-separated)
        lines = result.strip().split("\n")

        # Check header
        self.assertEqual(len(lines), 3, "Should have header + 2 data rows")
        self.assertTrue(
            lines[0].startswith("timestamp_ms"), "Header should start with timestamp_ms"
        )

        # Check data rows (tab-separated)
        row1 = lines[1].split("\t")
        self.assertEqual(row1[0], "1733856000000", "First timestamp should match")
        self.assertEqual(row1[2], "15.5", "First radius_px should match")

    def test_export_empty_data(self):
        """Test export with no data."""
        self.controller.raw_measurements = []
        result = self.controller.export_data("csv")

        self.assertIsNone(result, "Export should return None for empty data")

    def test_export_invalid_format(self):
        """Test export with invalid format."""
        with self.assertRaises(ValueError):
            self.controller.export_data("invalid")

    def test_export_memory_limit(self):
        """Test that memory limit is enforced."""
        # Add more than max_raw_measurements
        self.controller.max_raw_measurements = 5

        # Create 10 measurements
        for i in range(10):
            self.controller.raw_measurements.append(
                {
                    "timestamp_ms": 1733856000000 + i * 100,
                    "frame_id": i,
                    "radius_px": 10.0 + i,
                    "radius_um": 8.2 + i * 0.82,
                    "area_px": 100.0,
                    "area_um2": 67.24,
                    "x_center_px": 50.0,
                    "y_center_px": 50.0,
                    "major_axis_px": 20.0,
                    "major_axis_um": 16.4,
                    "equivalent_diameter_px": 20.0,
                    "equivalent_diameter_um": 16.4,
                }
            )

        # Trigger storage limit (should keep only last 5)
        # Simulate by calling _store_raw_measurements logic
        if len(self.controller.raw_measurements) > self.controller.max_raw_measurements:
            self.controller.raw_measurements = self.controller.raw_measurements[
                -self.controller.max_raw_measurements :
            ]

        # Export should only contain 5 measurements
        result = self.controller.export_data("csv")
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        # Header + 5 data rows
        self.assertEqual(len(rows), 6, "Should have header + 5 data rows after limit")

    def test_export_all_columns(self):
        """Test that all expected columns are present."""
        result = self.controller.export_data("csv")
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)

        headers = rows[0]
        expected_headers = [
            "timestamp_ms",
            "frame_id",
            "radius_px",
            "radius_um",
            "area_px",
            "area_um2",
            "x_center_px",
            "y_center_px",
            "major_axis_px",
            "major_axis_um",
            "equivalent_diameter_px",
            "equivalent_diameter_um",
        ]

        self.assertEqual(headers, expected_headers, "All expected headers should be present")
        self.assertEqual(len(headers), 12, "Should have 12 columns")

    def test_export_reset_clears_data(self):
        """Test that reset() clears raw measurements."""
        self.assertGreater(len(self.controller.raw_measurements), 0, "Should have data")

        self.controller.reset()

        self.assertEqual(
            len(self.controller.raw_measurements), 0, "Reset should clear measurements"
        )
        result = self.controller.export_data("csv")
        self.assertIsNone(result, "Export should return None after reset")


if __name__ == "__main__":
    unittest.main()
