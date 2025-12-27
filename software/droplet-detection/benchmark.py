"""
Performance benchmarking script for droplet detection pipeline.

Tests processing speed with various ROI sizes and droplet densities.
Generates performance reports and frame rate limit recommendations.

Usage:
    python -m droplet_detection.benchmark [--roi-size SMALL|MEDIUM|LARGE] [--iterations N]
"""

import argparse
import logging
import time
import numpy as np
import cv2
import sys
import os
from typing import Dict, List, Tuple, Optional, Any, Callable
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from droplet_detection import (
    DropletDetector,
    DropletDetectionConfig,
    Preprocessor,
    Segmenter,
    Measurer,
    ArtifactRejector,
    DropletHistogram,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Benchmark droplet detection performance with various scenarios."""

    # ROI size definitions (width, height)
    ROI_SIZES = {
        "small": (50, 256),
        "medium": (100, 512),
        "large": (150, 1024),
    }

    # Droplet density scenarios (droplets per frame)
    DENSITY_SCENARIOS = {
        "low": (1, 5),
        "medium": (5, 20),
        "high": (20, 50),
    }

    def __init__(self, iterations: int = 100):
        """
        Initialize benchmark.

        Args:
            iterations: Number of iterations per test scenario
        """
        self.iterations = iterations
        self.results: Dict[str, List[float]] = {}

    def generate_test_frame(
        self, width: int, height: int, num_droplets: int, noise_level: float = 0.1
    ) -> np.ndarray:
        """
        Generate synthetic test frame with droplets.

        Args:
            width: Frame width
            height: Frame height
            num_droplets: Number of droplets to generate
            noise_level: Gaussian noise level (0-1)

        Returns:
            Synthetic frame as numpy array (grayscale, uint8)
        """
        # Create background (slightly non-uniform)
        frame = np.ones((height, width), dtype=np.uint8) * 128

        # Add some background variation
        frame += np.random.randint(-20, 20, (height, width), dtype=np.int16)
        frame = np.clip(frame, 0, 255).astype(np.uint8)

        # Add droplets (dark ellipses on light background)
        for _ in range(num_droplets):
            # Random droplet parameters
            center_x = np.random.randint(20, width - 20)
            center_y = np.random.randint(20, height - 20)
            major_axis = np.random.randint(10, 30)
            minor_axis = np.random.randint(8, major_axis)
            angle = np.random.uniform(0, 360)

            # Draw ellipse (dark droplet)
            cv2.ellipse(
                frame,
                (center_x, center_y),
                (major_axis // 2, minor_axis // 2),
                angle,
                0,
                360,
                50,  # Dark gray (droplet)
                -1,  # Filled
            )

        # Add noise
        noise = np.random.normal(0, noise_level * 255, (height, width))
        frame = np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        return frame

    def benchmark_component(
        self, component_name: str, component_func: Callable, test_frame: np.ndarray, iterations: int
    ) -> Dict[str, float]:
        """
        Benchmark a single component.

        Args:
            component_name: Name of component
            component_func: Function to benchmark
            test_frame: Test frame to process
            iterations: Number of iterations

        Returns:
            Statistics dictionary (mean, std, min, max, p95, p99)
        """
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            try:
                result = component_func(test_frame)
            except Exception as e:
                logger.warning(f"Error in {component_name}: {e}")
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        if not times:
            return {}

        times_array = np.array(times)
        return {
            "mean": float(np.mean(times_array)),
            "std": float(np.std(times_array)),
            "min": float(np.min(times_array)),
            "max": float(np.max(times_array)),
            "p95": float(np.percentile(times_array, 95)),
            "p99": float(np.percentile(times_array, 99)),
        }

    def benchmark_pipeline(
        self,
        roi_size: Tuple[int, int],
        num_droplets: int,
        config: Optional[DropletDetectionConfig] = None,
    ) -> Dict[str, Any]:
        """
        Benchmark full detection pipeline.

        Args:
            roi_size: (width, height) tuple
            num_droplets: Number of droplets in test frame
            config: Optional configuration (uses default if None)

        Returns:
            Benchmark results dictionary
        """
        width, height = roi_size
        logger.info(f"Benchmarking: ROI={width}×{height}, droplets={num_droplets}")

        # Generate test frame
        test_frame = self.generate_test_frame(width, height, num_droplets)

        # Initialize components
        if config is None:
            config = DropletDetectionConfig()

        preprocessor = Preprocessor(config)
        segmenter = Segmenter(config)
        measurer = Measurer(config)
        artifact_rejector = ArtifactRejector(config)
        histogram = DropletHistogram(
            window_size=config.histogram_window_size, pixel_ratio=1.0, unit="px"
        )
        detector = DropletDetector(config)

        results = {
            "roi_size": roi_size,
            "num_droplets": num_droplets,
            "iterations": self.iterations,
        }

        # Benchmark preprocessing
        def preprocess_func(frame):
            return preprocessor.process(frame)

        results["preprocessing"] = self.benchmark_component(
            "preprocessing", preprocess_func, test_frame, self.iterations
        )

        # Benchmark segmentation (needs mask from preprocessing)
        mask = preprocessor.process(test_frame)

        def segment_func(m):
            return segmenter.detect_contours(m)

        results["segmentation"] = self.benchmark_component(
            "segmentation", segment_func, mask, self.iterations
        )

        # Benchmark measurement (needs contours from segmentation)
        contours = segmenter.detect_contours(mask)

        def measure_func(cs):
            return [measurer.measure(c) for c in cs]

        results["measurement"] = self.benchmark_component(
            "measurement", measure_func, contours, self.iterations
        )

        # Benchmark artifact rejection
        metrics = [measurer.measure(c) for c in contours]

        def reject_func(ms):
            return artifact_rejector.filter([m.contour for m in ms])

        results["artifact_rejection"] = self.benchmark_component(
            "artifact_rejection", reject_func, metrics, self.iterations
        )

        # Benchmark histogram update
        def histogram_func(ms):
            histogram.update(ms)

        results["histogram_update"] = self.benchmark_component(
            "histogram_update", histogram_func, metrics, self.iterations
        )

        # Benchmark full pipeline
        def full_pipeline_func(frame):
            return detector.process_frame(frame)

        results["total_per_frame"] = self.benchmark_component(
            "total_per_frame", full_pipeline_func, test_frame, self.iterations
        )

        # Calculate frame rate limits
        if "total_per_frame" in results and "mean" in results["total_per_frame"]:
            mean_ms = results["total_per_frame"]["mean"]
            max_fps = 1000.0 / mean_ms if mean_ms > 0 else 0
            p95_ms = results["total_per_frame"].get("p95", mean_ms)
            safe_fps = 1000.0 / p95_ms if p95_ms > 0 else 0

            results["frame_rate"] = {
                "max_fps": max_fps,
                "safe_fps": safe_fps,
                "mean_ms": mean_ms,
                "p95_ms": p95_ms,
            }

        return results

    def run_full_benchmark(
        self, roi_sizes: Optional[List[str]] = None, densities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run full benchmark suite.

        Args:
            roi_sizes: List of ROI size keys to test (default: all)
            densities: List of density keys to test (default: all)

        Returns:
            Complete benchmark results
        """
        if roi_sizes is None:
            roi_sizes = list(self.ROI_SIZES.keys())
        if densities is None:
            densities = list(self.DENSITY_SCENARIOS.keys())

        all_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "iterations_per_test": self.iterations,
            "scenarios": [],
        }

        for roi_key in roi_sizes:
            if roi_key not in self.ROI_SIZES:
                logger.warning(f"Unknown ROI size: {roi_key}")
                continue

            roi_size = self.ROI_SIZES[roi_key]

            for density_key in densities:
                if density_key not in self.DENSITY_SCENARIOS:
                    logger.warning(f"Unknown density: {density_key}")
                    continue

                min_drops, max_drops = self.DENSITY_SCENARIOS[density_key]
                # Use average for benchmark
                num_droplets = (min_drops + max_drops) // 2

                logger.info(f"Running benchmark: ROI={roi_key}, density={density_key}")
                scenario_results = self.benchmark_pipeline(roi_size, num_droplets)
                scenario_results["scenario"] = {
                    "roi_size_key": roi_key,
                    "density_key": density_key,
                }
                all_results["scenarios"].append(scenario_results)

        return all_results

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print benchmark summary."""
        print("\n" + "=" * 80)
        print("DROPLET DETECTION PERFORMANCE BENCHMARK")
        print("=" * 80)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Iterations per test: {results['iterations_per_test']}")
        print(f"Number of scenarios: {len(results['scenarios'])}")
        print("\n" + "-" * 80)

        for scenario in results["scenarios"]:
            roi = scenario["roi_size"]
            drops = scenario["num_droplets"]
            roi_key = scenario.get("scenario", {}).get("roi_size_key", "unknown")
            density_key = scenario.get("scenario", {}).get("density_key", "unknown")

            print(
                f"\nScenario: ROI={roi_key} ({roi[0]}×{roi[1]}), Density={density_key} ({drops} droplets)"
            )
            print("-" * 80)

            components = [
                "preprocessing",
                "segmentation",
                "measurement",
                "artifact_rejection",
                "histogram_update",
                "total_per_frame",
            ]

            for component in components:
                if component in scenario and scenario[component]:
                    stats = scenario[component]
                    print(
                        f"  {component:20s}: "
                        f"mean={stats['mean']:6.2f}ms, "
                        f"std={stats['std']:5.2f}ms, "
                        f"p95={stats['p95']:6.2f}ms"
                    )

            if "frame_rate" in scenario:
                fr = scenario["frame_rate"]
                print(f"\n  Frame Rate Limits:")
                print(f"    Max FPS: {fr['max_fps']:.1f}")
                print(f"    Safe FPS: {fr['safe_fps']:.1f} (p95)")

    def save_results(self, results: Dict[str, Any], output_path: str) -> None:
        """Save benchmark results to JSON file."""
        try:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_path}")
        except (IOError, OSError) as e:
            logger.error(f"Error saving results to {output_path}: {e}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Benchmark droplet detection performance")
    parser.add_argument(
        "--roi-size",
        choices=["small", "medium", "large", "all"],
        default="all",
        help="ROI size to test (default: all)",
    )
    parser.add_argument(
        "--density",
        choices=["low", "medium", "high", "all"],
        default="all",
        help="Droplet density to test (default: all)",
    )
    parser.add_argument(
        "--iterations", type=int, default=100, help="Number of iterations per test (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_results.json",
        help="Output JSON file path (default: benchmark_results.json)",
    )

    args = parser.parse_args()

    # Determine ROI sizes and densities to test
    roi_sizes = None if args.roi_size == "all" else [args.roi_size]
    densities = None if args.density == "all" else [args.density]

    # Run benchmark
    benchmark = PerformanceBenchmark(iterations=args.iterations)
    results = benchmark.run_full_benchmark(roi_sizes=roi_sizes, densities=densities)

    # Print summary
    benchmark.print_summary(results)

    # Save results
    benchmark.save_results(results, args.output)

    print(f"\n✓ Benchmark complete. Results saved to {args.output}")


if __name__ == "__main__":
    main()
