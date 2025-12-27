"""
Integration tests for droplet detection pipeline.

Tests the full pipeline with real test images from droplet_AInalysis.
Validates detection, histogram generation, and statistics.

Usage:
    python -m droplet_detection.test_integration [--images N]
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

# Add parent directory to path
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, software_dir)

# Import droplet_detection module (directory has hyphen, so use importlib)
import importlib.util

droplet_detection_path = os.path.join(software_dir, "droplet-detection")
if os.path.exists(droplet_detection_path):
    spec = importlib.util.spec_from_file_location(
        "droplet_detection", os.path.join(droplet_detection_path, "__init__.py")
    )
    droplet_detection = importlib.util.module_from_spec(spec)
    sys.modules["droplet_detection"] = droplet_detection
    spec.loader.exec_module(droplet_detection)

    DropletDetector = droplet_detection.DropletDetector
    DropletDetectionConfig = droplet_detection.DropletDetectionConfig
    DropletHistogram = droplet_detection.DropletHistogram

    # Import test_data_loader directly from file
    test_data_loader_spec = importlib.util.spec_from_file_location(
        "test_data_loader", os.path.join(droplet_detection_path, "test_data_loader.py")
    )
    test_data_loader = importlib.util.module_from_spec(test_data_loader_spec)
    test_data_loader_spec.loader.exec_module(test_data_loader)
    find_test_images = test_data_loader.find_test_images
    load_test_image = test_data_loader.load_test_image
else:
    raise ImportError("droplet-detection directory not found")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class IntegrationTest:
    """Integration tests for droplet detection."""

    def __init__(self, max_images: int = 10):
        """
        Initialize integration test.

        Args:
            max_images: Maximum number of test images to use
        """
        self.max_images = max_images
        self.test_images: List[np.ndarray] = []
        self.results: Dict[str, Any] = {
            "total_images": 0,
            "successful_detections": 0,
            "failed_detections": 0,
            "total_droplets": 0,
            "avg_droplets_per_frame": 0.0,
        }

    def load_test_images(self) -> bool:
        """Load test images from droplet_AInalysis repository."""
        logger.info("Loading test images...")

        image_paths = find_test_images()

        if not image_paths:
            logger.warning("No test images found. Trying alternative locations...")
            # Try direct path
            ai_analysis_path = (
                Path(__file__).parent.parent.parent.parent / "droplet_AInalysis" / "imgs"
            )
            if ai_analysis_path.exists():
                image_paths = list(ai_analysis_path.glob("*.jpg")) + list(
                    ai_analysis_path.glob("*.png")
                )
                image_paths = [str(p) for p in image_paths]

        if not image_paths:
            logger.error("No test images found. Cannot run integration tests.")
            return False

        # Load up to max_images
        loaded = 0
        for img_path in image_paths[: self.max_images]:
            try:
                img = load_test_image(img_path)
                if img is not None:
                    self.test_images.append(img)
                    loaded += 1
                    logger.debug(f"Loaded: {img_path}")
            except Exception as e:
                logger.warning(f"Error loading {img_path}: {e}")

        logger.info(f"Loaded {len(self.test_images)} test images")
        return len(self.test_images) > 0

    def test_detection_pipeline(self, config: Optional[DropletDetectionConfig] = None) -> bool:
        """
        Test full detection pipeline on test images.

        Args:
            config: Optional configuration (uses default if None)

        Returns:
            True if all tests passed
        """
        if not self.test_images:
            logger.error("No test images loaded")
            return False

        if config is None:
            config = DropletDetectionConfig()

        detector = DropletDetector(config)
        histogram = DropletHistogram(window_size=100, pixel_ratio=1.0, unit="px")

        logger.info(f"Testing detection pipeline on {len(self.test_images)} images...")

        all_passed = True

        for i, img in enumerate(self.test_images):
            try:
                # Convert to grayscale if needed
                if len(img.shape) == 3:
                    gray = np.mean(img, axis=2).astype(np.uint8)
                else:
                    gray = img

                # Process frame
                metrics = detector.process_frame(gray)

                # Update histogram
                histogram.update(metrics)

                # Record results
                num_droplets = len(metrics)
                self.results["total_droplets"] += num_droplets
                self.results["successful_detections"] += 1

                logger.debug(f"Image {i+1}: Detected {num_droplets} droplets")

            except Exception as e:
                logger.error(f"Error processing image {i+1}: {e}")
                self.results["failed_detections"] += 1
                all_passed = False

        self.results["total_images"] = len(self.test_images)
        if self.results["total_images"] > 0:
            self.results["avg_droplets_per_frame"] = (
                self.results["total_droplets"] / self.results["total_images"]
            )

        return all_passed

    def test_histogram_generation(self) -> bool:
        """Test histogram generation and statistics."""
        logger.info("Testing histogram generation...")

        histogram = DropletHistogram(window_size=100, pixel_ratio=1.0, unit="px")

        # Create some dummy metrics
        from droplet_detection import DropletMetrics
        import cv2

        dummy_contours = []
        for i in range(5):
            # Create a simple circle contour
            center = (50 + i * 10, 50 + i * 10)
            radius = 10 + i * 2
            circle = np.zeros((100, 100), dtype=np.uint8)
            cv2.circle(circle, center, radius, 255, -1)
            contours, _ = cv2.findContours(circle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                dummy_contours.extend(contours)

        # Measure and update
        from droplet_detection import Measurer

        measurer = Measurer(DropletDetectionConfig())
        metrics = [measurer.measure(c) for c in dummy_contours]

        histogram.update(metrics)

        # Test histogram retrieval
        try:
            width_hist = histogram.get_histogram("width")
            height_hist = histogram.get_histogram("height")
            area_hist = histogram.get_histogram("area")
            diameter_hist = histogram.get_histogram("diameter")

            stats = histogram.get_statistics()

            logger.info("Histogram generation test passed")
            logger.debug(f"Statistics: {stats}")
            return True

        except Exception as e:
            logger.error(f"Histogram generation test failed: {e}")
            return False

    def test_config_loading(self) -> bool:
        """Test configuration loading and validation."""
        logger.info("Testing configuration management...")

        try:
            # Test default config
            config = DropletDetectionConfig()
            is_valid, errors = config.validate()
            if not is_valid:
                logger.error(f"Default config invalid: {errors}")
                return False

            # Test config update
            config.update({"min_area": 50, "max_area": 5000})
            is_valid, errors = config.validate()
            if not is_valid:
                logger.error(f"Updated config invalid: {errors}")
                return False

            # Test to_dict and from_dict
            config_dict = config.to_dict()
            new_config = DropletDetectionConfig(config_dict=config_dict)
            is_valid, errors = new_config.validate()
            if not is_valid:
                logger.error(f"Reconstructed config invalid: {errors}")
                return False

            logger.info("Configuration management test passed")
            return True

        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False

    def print_results(self) -> None:
        """Print test results summary."""
        print("\n" + "=" * 80)
        print("INTEGRATION TEST RESULTS")
        print("=" * 80)
        print(f"Total images tested: {self.results['total_images']}")
        print(f"Successful detections: {self.results['successful_detections']}")
        print(f"Failed detections: {self.results['failed_detections']}")
        print(f"Total droplets detected: {self.results['total_droplets']}")
        print(f"Average droplets per frame: {self.results['avg_droplets_per_frame']:.2f}")
        print("=" * 80)

    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        logger.info("Starting integration tests...")

        all_passed = True

        # Test 1: Configuration
        if not self.test_config_loading():
            all_passed = False

        # Test 2: Histogram generation
        if not self.test_histogram_generation():
            all_passed = False

        # Test 3: Load test images
        if not self.load_test_images():
            logger.warning("Skipping detection pipeline test (no images)")
            return all_passed

        # Test 4: Detection pipeline
        if not self.test_detection_pipeline():
            all_passed = False

        self.print_results()

        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run integration tests for droplet detection")
    parser.add_argument(
        "--images", type=int, default=10, help="Maximum number of test images to use (default: 10)"
    )
    parser.add_argument("--config", type=str, help="Path to configuration JSON file (optional)")

    args = parser.parse_args()

    # Load config if provided
    config = None
    if args.config:
        from droplet_detection import load_config

        config = load_config(args.config)

    # Run tests
    test = IntegrationTest(max_images=args.images)
    success = test.run_all_tests()

    if success:
        print("\n✓ All integration tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some integration tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
