"""
Comprehensive tests for droplet measurement methods.

This test suite verifies:
1. How measurement methods work
2. Radius offset correction accuracy
3. Measurement accuracy with known shapes
4. Edge cases and error handling
"""

import unittest
import numpy as np
import cv2
import sys
import os
import importlib.util

# Add parent directory to path
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, software_dir)

# Import droplet-detection module (handles hyphen in directory name)
droplet_detection_path = os.path.join(software_dir, "droplet-detection")
if os.path.exists(droplet_detection_path):
    spec = importlib.util.spec_from_file_location(
        "droplet_detection", os.path.join(droplet_detection_path, "__init__.py")
    )
    droplet_detection = importlib.util.module_from_spec(spec)
    sys.modules["droplet_detection"] = droplet_detection
    spec.loader.exec_module(droplet_detection)

    Measurer = droplet_detection.Measurer
    DropletMetrics = droplet_detection.DropletMetrics
    DropletDetectionConfig = droplet_detection.DropletDetectionConfig
else:
    # Fallback to direct import (if installed as package)
    from droplet_detection.measurer import Measurer
    from droplet_detection.config import DropletDetectionConfig


class TestMeasurementMethods(unittest.TestCase):
    """
    Test suite for understanding and verifying measurement methods.

    Measurement Process:
    1. Contour Area: cv2.contourArea() - pixel area of the droplet
    2. Bounding Box: cv2.boundingRect() - smallest rectangle enclosing contour
    3. Centroid: Calculated from image moments (center of mass)
    4. Ellipse Fitting: cv2.fitEllipse() - fits ellipse to contour, major axis = longest dimension
    5. Equivalent Diameter: sqrt(4 * area / π) - diameter of circle with same area
    6. Radius Offset Correction: Applies pixel offset to correct for threshold bias
    """

    def setUp(self):
        """Set up test fixtures."""
        self.config = DropletDetectionConfig()
        self.measurer = Measurer(self.config)

    def create_circle_contour(self, center: tuple, radius: int) -> np.ndarray:
        """
        Create a perfect circle contour for testing.

        Args:
            center: (x, y) center coordinates
            radius: Circle radius in pixels

        Returns:
            Contour array
        """
        # Create image with circle
        img = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(img, center, radius, 255, -1)  # Filled circle

        # Extract contour
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.assertGreater(len(contours), 0, "Failed to create circle contour")
        return contours[0]

    def test_measurement_workflow_explanation(self):
        """
        Test and explain the measurement workflow.

        Workflow:
        1. For each contour:
           a. Calculate area (pixels²)
           b. Get bounding box (x, y, width, height)
           c. Calculate centroid (center of mass)
           d. Fit ellipse to get major axis (longest dimension)
           e. Calculate equivalent diameter (diameter of circle with same area)
           f. Apply radius offset correction
        2. Return list of DropletMetrics
        """
        # Create a test circle
        center = (100, 100)
        true_radius = 30
        contour = self.create_circle_contour(center, true_radius)

        # Measure without offset
        metrics = self.measurer.measure([contour], radius_offset_px=0.0)
        self.assertEqual(len(metrics), 1)

        m = metrics[0]

        # Verify all metrics are calculated
        self.assertGreater(m.area, 0, "Area should be positive")
        self.assertGreater(m.major_axis, 0, "Major axis should be positive")
        self.assertGreater(m.equivalent_diameter, 0, "Equivalent diameter should be positive")
        self.assertEqual(len(m.centroid), 2, "Centroid should have (x, y) coordinates")
        self.assertEqual(len(m.bounding_box), 4, "Bounding box should have (x, y, w, h)")

        print("\n=== Measurement Results (no offset) ===")
        print(f"True radius: {true_radius} px")
        print(f"Area: {m.area:.2f} px²")
        print(f"Equivalent diameter: {m.equivalent_diameter:.2f} px")
        print(f"Measured radius (diameter/2): {m.equivalent_diameter/2:.2f} px")
        print(f"Major axis: {m.major_axis:.2f} px")
        print(f"Centroid: {m.centroid}")
        print(f"Bounding box: {m.bounding_box}")

    def test_radius_offset_correction(self):
        """
        Test radius offset correction.

        The offset correction works as follows:
        1. Calculate raw radius from equivalent diameter: radius = diameter / 2
        2. Apply offset: corrected_radius = raw_radius + offset
        3. Convert back to diameter: corrected_diameter = corrected_radius * 2

        For a negative offset (e.g., -2.0 px):
        - If raw radius = 30 px, corrected = 30 - 2 = 28 px
        - Diameter changes from 60 px to 56 px (difference of 4 px = 2 * offset)
        """
        # Create circle with known radius
        true_radius = 30
        contour = self.create_circle_contour((100, 100), true_radius)

        # Measure without offset
        metrics_no_offset = self.measurer.measure([contour], radius_offset_px=0.0)
        self.assertEqual(len(metrics_no_offset), 1)
        diameter_no_offset = metrics_no_offset[0].equivalent_diameter

        # Measure with negative offset (should reduce size)
        offset = -2.0
        metrics_with_offset = self.measurer.measure([contour], radius_offset_px=offset)
        self.assertEqual(len(metrics_with_offset), 1)
        diameter_with_offset = metrics_with_offset[0].equivalent_diameter

        # Verify offset is applied correctly
        # Diameter difference should be 2 * offset (since diameter = 2 * radius)
        expected_difference = 2 * abs(offset)  # 4.0 px
        actual_difference = diameter_no_offset - diameter_with_offset

        print("\n=== Radius Offset Correction Test ===")
        print(f"True radius: {true_radius} px")
        print(f"Offset: {offset} px")
        print(f"Diameter (no offset): {diameter_no_offset:.2f} px")
        print(f"Diameter (with offset): {diameter_with_offset:.2f} px")
        print(f"Expected difference: {expected_difference:.2f} px")
        print(f"Actual difference: {actual_difference:.2f} px")

        # Allow small tolerance for pixel discretization
        self.assertAlmostEqual(
            actual_difference,
            expected_difference,
            places=1,
            msg=f"Offset correction not applied correctly. Expected difference {expected_difference}, got {actual_difference}",
        )

        # Verify diameter with offset is smaller (for negative offset)
        self.assertLess(
            diameter_with_offset, diameter_no_offset, "Negative offset should reduce diameter"
        )

    def test_radius_offset_positive(self):
        """Test positive radius offset (increases measured size)."""
        contour = self.create_circle_contour((100, 100), 30)

        # Measure without offset
        metrics_no_offset = self.measurer.measure([contour], radius_offset_px=0.0)
        diameter_no_offset = metrics_no_offset[0].equivalent_diameter

        # Measure with positive offset (should increase size)
        offset = 2.0
        metrics_with_offset = self.measurer.measure([contour], radius_offset_px=offset)
        diameter_with_offset = metrics_with_offset[0].equivalent_diameter

        # Verify diameter increased
        self.assertGreater(
            diameter_with_offset, diameter_no_offset, "Positive offset should increase diameter"
        )

        # Verify difference is approximately 2 * offset
        difference = diameter_with_offset - diameter_no_offset
        expected_difference = 2 * offset
        self.assertAlmostEqual(difference, expected_difference, places=1)

    def test_radius_offset_major_axis(self):
        """
        Test that radius offset is also applied to major_axis.

        Major axis is the longest dimension from ellipse fitting.
        It should also be corrected with the same offset.
        """
        contour = self.create_circle_contour((100, 100), 30)

        # Measure without offset
        metrics_no_offset = self.measurer.measure([contour], radius_offset_px=0.0)
        major_axis_no_offset = metrics_no_offset[0].major_axis

        # Measure with offset
        offset = -2.0
        metrics_with_offset = self.measurer.measure([contour], radius_offset_px=offset)
        major_axis_with_offset = metrics_with_offset[0].major_axis

        # Verify major axis is also corrected
        difference = major_axis_no_offset - major_axis_with_offset
        expected_difference = 2 * abs(offset)  # 4.0 px

        print("\n=== Major Axis Offset Correction ===")
        print(f"Major axis (no offset): {major_axis_no_offset:.2f} px")
        print(f"Major axis (with offset): {major_axis_with_offset:.2f} px")
        print(f"Expected difference: {expected_difference:.2f} px")
        print(f"Actual difference: {difference:.2f} px")

        self.assertAlmostEqual(difference, expected_difference, places=1)

    def test_negative_radius_protection(self):
        """
        Test that negative radius is prevented after offset correction.

        If offset is very negative, corrected radius could become negative.
        The code should ensure radius >= 0.
        """
        # Create small circle
        contour = self.create_circle_contour((100, 100), 5)

        # Apply very large negative offset (would make radius negative)
        large_negative_offset = -10.0

        metrics = self.measurer.measure([contour], radius_offset_px=large_negative_offset)
        self.assertEqual(len(metrics), 1)

        # Verify diameter is non-negative (or very small but >= 0)
        self.assertGreaterEqual(
            metrics[0].equivalent_diameter,
            0.0,
            "Diameter should not be negative after offset correction",
        )

        # For very small circles with large negative offset, diameter might be 0
        # This is expected behavior (protection against negative radius)

    def test_multiple_contours(self):
        """Test measurement of multiple contours."""
        # Create multiple circles
        contours = [
            self.create_circle_contour((50, 50), 20),
            self.create_circle_contour((150, 50), 25),
            self.create_circle_contour((100, 150), 30),
        ]

        metrics = self.measurer.measure(contours, radius_offset_px=0.0)

        self.assertEqual(len(metrics), 3, "Should measure all contours")

        # Verify each metric is valid
        for m in metrics:
            self.assertGreater(m.area, 0)
            self.assertGreater(m.equivalent_diameter, 0)
            self.assertGreater(m.major_axis, 0)

    def test_ellipse_fitting_fallback(self):
        """
        Test ellipse fitting fallback behavior.

        If ellipse fitting fails or contour has too few points,
        major_axis falls back to bounding box max dimension.
        """
        # Create contour with very few points (might fail ellipse fitting)
        contour = np.array(
            [
                [[10, 10]],
                [[20, 10]],
                [[20, 20]],
                [[10, 20]],
            ],
            dtype=np.int32,
        )

        # This should still work (fallback to bounding box)
        metrics = self.measurer.measure([contour], radius_offset_px=0.0)
        self.assertEqual(len(metrics), 1)

        # Major axis should be calculated (either from ellipse or bounding box)
        self.assertGreater(metrics[0].major_axis, 0)

    def test_area_preservation(self):
        """
        Test that area is NOT affected by radius offset.

        Area is measured directly from contour and should not change
        with offset correction. Only diameter and major_axis are corrected.
        """
        contour = self.create_circle_contour((100, 100), 30)

        # Measure with different offsets
        metrics_no_offset = self.measurer.measure([contour], radius_offset_px=0.0)
        metrics_with_offset = self.measurer.measure([contour], radius_offset_px=-2.0)

        # Area should be the same
        self.assertEqual(
            metrics_no_offset[0].area,
            metrics_with_offset[0].area,
            "Area should not change with offset correction",
        )

    def test_centroid_calculation(self):
        """Test centroid calculation accuracy."""
        # Create circle at known center
        center = (100, 100)
        contour = self.create_circle_contour(center, 30)

        metrics = self.measurer.measure([contour], radius_offset_px=0.0)
        centroid = metrics[0].centroid

        # Centroid should be close to circle center
        # (allowing for pixel discretization)
        self.assertAlmostEqual(centroid[0], center[0], delta=2.0)
        self.assertAlmostEqual(centroid[1], center[1], delta=2.0)

    def test_equivalent_diameter_formula(self):
        """
        Test equivalent diameter calculation.

        Equivalent diameter = sqrt(4 * area / π)
        This is the diameter of a circle with the same area as the contour.
        """
        # Create circle with known radius
        true_radius = 30
        true_area = np.pi * true_radius**2
        true_diameter = 2 * true_radius

        contour = self.create_circle_contour((100, 100), true_radius)
        metrics = self.measurer.measure([contour], radius_offset_px=0.0)

        # Verify equivalent diameter formula
        measured_area = metrics[0].area
        measured_diameter = metrics[0].equivalent_diameter

        # Calculate expected diameter from measured area
        expected_diameter = np.sqrt(4 * measured_area / np.pi)

        print("\n=== Equivalent Diameter Formula Test ===")
        print(f"True radius: {true_radius} px")
        print(f"True area: {true_area:.2f} px²")
        print(f"Measured area: {measured_area:.2f} px²")
        print(f"True diameter: {true_diameter} px")
        print(f"Measured diameter: {measured_diameter:.2f} px")
        print(f"Expected diameter (from area): {expected_diameter:.2f} px")

        # Verify formula is correct (allowing for pixel discretization)
        self.assertAlmostEqual(
            measured_diameter,
            expected_diameter,
            places=1,
            msg="Equivalent diameter should match sqrt(4*area/π)",
        )


def run_tests():
    """Run all tests and print summary."""
    print("=" * 70)
    print("Droplet Measurement Methods Test Suite")
    print("=" * 70)
    print("\nThis test suite verifies:")
    print("1. How measurement methods work")
    print("2. Radius offset correction accuracy")
    print("3. Measurement accuracy with known shapes")
    print("4. Edge cases and error handling")
    print("\n" + "=" * 70 + "\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMeasurementMethods)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(
        f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%"
    )

    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
