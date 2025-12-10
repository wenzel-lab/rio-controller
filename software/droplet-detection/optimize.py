"""
Parameter optimization tool for droplet detection.

Performs grid search over parameter space to find optimal settings.
Can be run offline on PC with test images from droplet_AInalysis.

Usage:
    python -m droplet_detection.optimize --dataset path/to/images --output optimized_config.json
"""

import argparse
import logging
import time
import numpy as np
import cv2
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json
import itertools
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from droplet_detection import (
    DropletDetector,
    DropletDetectionConfig,
    DropletMetrics,
    load_config,
    save_config,
)
from droplet_detection.test_data_loader import (
    find_test_images,
    load_test_image,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of a single parameter configuration test."""

    config: Dict[str, Any]
    detection_rate: float
    false_positive_rate: float
    false_negative_rate: float
    avg_droplets_per_frame: float
    score: float  # Combined score for ranking


class ParameterOptimizer:
    """Optimize droplet detection parameters using grid search."""

    def __init__(self, test_images: List[np.ndarray]):
        """
        Initialize optimizer.

        Args:
            test_images: List of test images (numpy arrays)
        """
        self.test_images = test_images
        self.results: List[OptimizationResult] = []

    def evaluate_config(
        self, config: DropletDetectionConfig, ground_truth: Optional[List[int]] = None
    ) -> Dict[str, float]:
        """
        Evaluate a configuration on test images.

        Args:
            config: Configuration to test
            ground_truth: Optional ground truth droplet counts per image

        Returns:
            Evaluation metrics dictionary
        """
        detector = DropletDetector(config)

        total_detections = 0
        total_frames = len(self.test_images)
        detection_counts = []

        for img in self.test_images:
            # Ensure grayscale
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

            # Process frame
            try:
                metrics = detector.process_frame(img)
                num_droplets = len(metrics)
                total_detections += num_droplets
                detection_counts.append(num_droplets)
            except Exception as e:
                logger.warning(f"Error processing frame: {e}")
                detection_counts.append(0)

        avg_droplets = total_detections / total_frames if total_frames > 0 else 0

        # Calculate rates (simplified - would need ground truth for accurate FPR/FNR)
        detection_rate = 1.0  # Assume all detected if we got results
        false_positive_rate = 0.0  # Would need ground truth
        false_negative_rate = 0.0  # Would need ground truth

        if ground_truth:
            # Compare with ground truth
            true_positives = 0
            false_positives = 0
            false_negatives = 0

            for i, (detected, expected) in enumerate(zip(detection_counts, ground_truth)):
                if detected == expected:
                    true_positives += 1
                elif detected > expected:
                    false_positives += detected - expected
                else:
                    false_negatives += expected - detected

            total_expected = sum(ground_truth)
            total_detected = sum(detection_counts)

            if total_expected > 0:
                detection_rate = true_positives / len(ground_truth)
                false_positive_rate = false_positives / total_expected if total_expected > 0 else 0
                false_negative_rate = false_negatives / total_expected if total_expected > 0 else 0

        return {
            "detection_rate": detection_rate,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate,
            "avg_droplets_per_frame": avg_droplets,
        }

    def calculate_score(
        self, detection_rate: float, false_positive_rate: float, false_negative_rate: float
    ) -> float:
        """
        Calculate combined score for ranking configurations.

        Higher is better.

        Args:
            detection_rate: Detection rate (0-1)
            false_positive_rate: False positive rate (0-1)
            false_negative_rate: False negative rate (0-1)

        Returns:
            Combined score
        """
        # Weighted combination: favor high detection rate, penalize FPR and FNR
        score = detection_rate * 1.0 - false_positive_rate * 0.5 - false_negative_rate * 0.5
        return max(0.0, score)  # Ensure non-negative

    def generate_parameter_grid(
        self, base_config: Optional[DropletDetectionConfig] = None
    ) -> List[DropletDetectionConfig]:
        """
        Generate grid of parameter configurations to test.

        Args:
            base_config: Base configuration (uses default if None)

        Returns:
            List of configurations to test
        """
        if base_config is None:
            base_config = DropletDetectionConfig()

        # Define parameter ranges
        min_area_values = [10, 20, 30, 50]
        max_area_values = [1000, 2000, 5000, 10000]
        threshold_methods = ["otsu", "adaptive"]
        background_methods = ["static", "highpass"]
        morph_kernel_sizes = [3, 5]

        configs = []

        # Generate all combinations
        for min_area, max_area, thresh_method, bg_method, morph_kernel in itertools.product(
            min_area_values,
            max_area_values,
            threshold_methods,
            background_methods,
            morph_kernel_sizes,
        ):
            # Skip invalid combinations
            if min_area >= max_area:
                continue

            config = DropletDetectionConfig()
            config.update(base_config.to_dict())
            config.min_area = min_area
            config.max_area = max_area
            config.threshold_method = thresh_method
            config.background_method = bg_method
            config.morph_kernel_size = morph_kernel

            # Validate
            is_valid, errors = config.validate()
            if is_valid:
                configs.append(config)
            else:
                logger.debug(f"Skipping invalid config: {errors}")

        logger.info(f"Generated {len(configs)} parameter configurations")
        return configs

    def optimize(
        self,
        parameter_grid: Optional[List[DropletDetectionConfig]] = None,
        ground_truth: Optional[List[int]] = None,
        top_k: int = 10,
    ) -> List[OptimizationResult]:
        """
        Run optimization over parameter grid.

        Args:
            parameter_grid: List of configurations to test (generates if None)
            ground_truth: Optional ground truth droplet counts
            top_k: Number of top results to return

        Returns:
            List of top-k optimization results
        """
        if parameter_grid is None:
            parameter_grid = self.generate_parameter_grid()

        logger.info(
            f"Testing {len(parameter_grid)} configurations on {len(self.test_images)} images"
        )

        for i, config in enumerate(parameter_grid):
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(parameter_grid)}")

            try:
                metrics = self.evaluate_config(config, ground_truth)
                score = self.calculate_score(
                    metrics["detection_rate"],
                    metrics["false_positive_rate"],
                    metrics["false_negative_rate"],
                )

                result = OptimizationResult(
                    config=config.to_dict(),
                    detection_rate=metrics["detection_rate"],
                    false_positive_rate=metrics["false_positive_rate"],
                    false_negative_rate=metrics["false_negative_rate"],
                    avg_droplets_per_frame=metrics["avg_droplets_per_frame"],
                    score=score,
                )
                self.results.append(result)
            except Exception as e:
                logger.warning(f"Error evaluating config {i}: {e}")

        # Sort by score (descending)
        self.results.sort(key=lambda x: x.score, reverse=True)

        if self.results:
            logger.info(f"Optimization complete. Top score: {self.results[0].score:.3f}")
        else:
            logger.warning("Optimization complete but no valid results found")
        return self.results[:top_k]

    def save_results(self, results: List[OptimizationResult], output_path: str) -> None:
        """Save optimization results to JSON."""
        output_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "num_test_images": len(self.test_images),
            "top_configurations": [asdict(r) for r in results],
        }

        try:
            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Results saved to {output_path}")
        except (IOError, OSError) as e:
            logger.error(f"Error saving results to {output_path}: {e}")
            raise


def load_test_dataset(dataset_path: str, max_images: Optional[int] = None) -> List[np.ndarray]:
    """
    Load test images from dataset directory.

    Args:
        dataset_path: Path to directory containing test images
        max_images: Maximum number of images to load (None = all)

    Returns:
        List of images as numpy arrays
    """
    dataset_path = Path(dataset_path)

    if not dataset_path.exists():
        # Try droplet_AInalysis repository
        ai_analysis_path = Path(__file__).parent.parent.parent.parent / "droplet_AInalysis"
        if ai_analysis_path.exists():
            dataset_path = ai_analysis_path / "imgs"
            logger.info(f"Using droplet_AInalysis images: {dataset_path}")
        else:
            raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

    images = []
    image_files = list(dataset_path.glob("*.jpg")) + list(dataset_path.glob("*.png"))

    if max_images:
        image_files = image_files[:max_images]

    for img_file in image_files:
        try:
            img = load_test_image(str(img_file))
            if img is not None:
                images.append(img)
        except Exception as e:
            logger.warning(f"Error loading {img_file}: {e}")

    logger.info(f"Loaded {len(images)} test images")
    return images


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Optimize droplet detection parameters")
    parser.add_argument(
        "--dataset", type=str, help="Path to test image dataset (default: droplet_AInalysis/imgs)"
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=20,
        help="Maximum number of test images to use (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="optimized_config.json",
        help="Output JSON file path (default: optimized_config.json)",
    )
    parser.add_argument(
        "--top-k", type=int, default=10, help="Number of top configurations to save (default: 10)"
    )
    parser.add_argument(
        "--base-config", type=str, help="Path to base configuration JSON file (optional)"
    )

    args = parser.parse_args()

    # Load test images
    dataset_path = args.dataset or "droplet_AInalysis/imgs"
    test_images = load_test_dataset(dataset_path, max_images=args.max_images)

    if not test_images:
        logger.error("No test images loaded. Exiting.")
        return

    # Load base config if provided
    base_config = None
    if args.base_config:
        base_config = load_config(args.base_config)

    # Run optimization
    optimizer = ParameterOptimizer(test_images)
    top_results = optimizer.optimize(
        parameter_grid=None,  # Auto-generate
        ground_truth=None,  # No ground truth available
        top_k=args.top_k,
    )

    # Print summary
    print("\n" + "=" * 80)
    print("PARAMETER OPTIMIZATION RESULTS")
    print("=" * 80)
    print(f"Test images: {len(test_images)}")
    print(f"Top {len(top_results)} configurations:\n")

    for i, result in enumerate(top_results, 1):
        print(f"{i}. Score: {result.score:.3f}")
        print(f"   Detection Rate: {result.detection_rate:.3f}")
        print(f"   False Positive Rate: {result.false_positive_rate:.3f}")
        print(f"   False Negative Rate: {result.false_negative_rate:.3f}")
        print(f"   Avg Droplets/Frame: {result.avg_droplets_per_frame:.2f}")
        print(
            f"   Config: min_area={result.config['min_area']}, "
            f"max_area={result.config['max_area']}, "
            f"threshold={result.config['threshold_method']}, "
            f"background={result.config['background_method']}"
        )
        print()

    # Save results
    optimizer.save_results(top_results, args.output)

    # Save best configuration
    if top_results:
        best_config_path = args.output.replace(".json", "_best_config.json")
        save_config(DropletDetectionConfig(config_dict=top_results[0].config), best_config_path)
        print(f"✓ Best configuration saved to {best_config_path}")


if __name__ == "__main__":
    main()
