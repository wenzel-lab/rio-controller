"""
Test script for droplet detection pipeline.

Tests the detector with images from droplet_AInalysis repository.
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from droplet_detection import DropletDetector, DropletDetectionConfig, DropletHistogram
from droplet_detection.test_data_loader import (
    find_test_images,
    load_test_image,
    extract_roi_from_image,
    get_default_roi_for_test_image,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_detector_on_image(image_path: str, roi: tuple = None):
    """
    Test detector on a single image.

    Args:
        image_path: Path to test image
        roi: Optional ROI tuple (x, y, width, height)
    """
    logger.info(f"Testing detector on: {image_path}")

    # Load image
    try:
        image = load_test_image(image_path)
        logger.info(f"Loaded image: {image.shape}")
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return

    # Get ROI
    if roi is None:
        roi = get_default_roi_for_test_image(image)
        logger.info(f"Using default ROI: {roi}")

    roi_image = extract_roi_from_image(image, roi)
    logger.info(f"ROI image shape: {roi_image.shape}")

    # Create detector
    config = DropletDetectionConfig()
    detector = DropletDetector(roi, config)

    # Initialize background (use the ROI image itself as background)
    # In real usage, you'd collect multiple frames
    logger.info("Initializing background...")
    for _ in range(config.background_frames):
        detector.preprocessor.initialize_background(roi_image)

    if not detector.preprocessor.background_initialized:
        logger.warning("Background not fully initialized, but continuing...")

    # Process frame
    logger.info("Processing frame...")
    metrics = detector.process_frame(roi_image)

    logger.info(f"Detected {len(metrics)} droplets")

    # Print metrics
    for i, m in enumerate(metrics):
        logger.info(
            f"Droplet {i+1}: "
            f"length={m.major_axis:.2f}px, "
            f"area={m.area:.2f}px², "
            f"diameter={m.equivalent_diameter:.2f}px, "
            f"centroid=({m.centroid[0]:.1f}, {m.centroid[1]:.1f})"
        )

    # Test histogram
    histogram = DropletHistogram(pixel_ratio=1.0, unit="px")
    histogram.update(metrics)

    stats = histogram.get_statistics()
    logger.info(f"\nStatistics:")
    logger.info(f"  Count: {stats['count']}")
    logger.info(f"  Width - mean: {stats['width']['mean']:.2f}, std: {stats['width']['std']:.2f}")
    logger.info(
        f"  Height - mean: {stats['height']['mean']:.2f}, std: {stats['height']['std']:.2f}"
    )
    logger.info(f"  Area - mean: {stats['area']['mean']:.2f}, std: {stats['area']['std']:.2f}")

    return metrics, histogram


def main():
    """Main test function."""
    logger.info("Starting droplet detector tests")

    # Find test images
    test_images = find_test_images()

    if not test_images:
        logger.warning("No test images found. Please check droplet_AInalysis repository path.")
        logger.info("Trying to create a simple test with synthetic data...")
        # Could add synthetic test here
        return

    logger.info(f"Found {len(test_images)} test images")

    # Test on first few images
    for image_path in test_images[:3]:  # Test first 3 images
        try:
            test_detector_on_image(image_path)
            logger.info("-" * 60)
        except Exception as e:
            logger.error(f"Error testing {image_path}: {e}", exc_info=True)

    logger.info("Tests complete")


if __name__ == "__main__":
    main()
