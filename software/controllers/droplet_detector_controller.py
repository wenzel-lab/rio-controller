"""
Droplet detector controller for real-time droplet detection.

Integrates droplet detection with existing camera and strobe systems.
Implements threading architecture and performance monitoring.
"""

import logging
import threading
import time
import queue
from typing import Optional, Dict, Any, List, cast
import numpy as np

# Add parent directory to path for imports
import sys
import os
import importlib.util

# Handle import of droplet-detection (hyphenated directory name)
software_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, software_dir)

# Import droplet_detection module (directory is droplet-detection, but we import as droplet_detection)
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
    load_config = droplet_detection.load_config
    save_config = droplet_detection.save_config
else:
    # Fallback: try direct import (if directory was renamed)
    from droplet_detection import (  # noqa: E402
        DropletDetector,
        DropletDetectionConfig,
        DropletHistogram,
        load_config,
        save_config,
    )
from controllers.camera import Camera  # noqa: E402
from controllers.strobe_cam import PiStrobeCam  # noqa: E402

logger = logging.getLogger(__name__)


class TimingInstrumentation:
    """
    Timing instrumentation for performance monitoring.

    Tracks processing times for each component of the detection pipeline.
    """

    def __init__(self, max_samples: int = 1000):
        """
        Initialize timing instrumentation.

        Args:
            max_samples: Maximum number of samples to store per component
        """
        self.max_samples = max_samples
        self.timings: Dict[str, List[float]] = {
            "preprocessing": [],
            "segmentation": [],
            "artifact_rejection": [],
            "measurement": [],
            "histogram_update": [],
            "total_per_frame": [],
        }
        self.lock = threading.Lock()

    def time_component(self, component: str, func, *args, **kwargs):
        """
        Time a function call and store the result.

        Args:
            component: Component name (key in timings dict)
            func: Function to time
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000  # Convert to ms

        with self.lock:
            if component in self.timings:
                self.timings[component].append(elapsed_ms)
                # Keep only last max_samples
                if len(self.timings[component]) > self.max_samples:
                    self.timings[component].pop(0)

        return result

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get timing statistics for each component.

        Returns:
            Dictionary of component statistics (mean, std, min, max, p95, p99)
        """
        stats = {}

        with self.lock:
            for component, times in self.timings.items():
                if times:
                    times_array = np.array(times)
                    stats[component] = {
                        "mean": float(np.mean(times_array)),
                        "std": float(np.std(times_array)),
                        "min": float(np.min(times_array)),
                        "max": float(np.max(times_array)),
                        "p95": float(np.percentile(times_array, 95)),
                        "p99": float(np.percentile(times_array, 99)),
                        "count": len(times),
                    }
                else:
                    stats[component] = {
                        "mean": 0.0,
                        "std": 0.0,
                        "min": 0.0,
                        "max": 0.0,
                        "p95": 0.0,
                        "p99": 0.0,
                        "count": 0,
                    }

        return stats

    def reset(self) -> None:
        """Reset all timing data."""
        with self.lock:
            for component in self.timings:
                self.timings[component].clear()


class DropletDetectorController:
    """
    Controller for droplet detection system.

    Integrates with existing Camera and PiStrobeCam systems to provide
    real-time droplet detection with histogram generation and statistics.
    """

    def __init__(
        self,
        camera: Camera,
        strobe_cam: PiStrobeCam,
        config: Optional[DropletDetectionConfig] = None,
        config_path: Optional[str] = None,
    ):
        """
        Initialize droplet detector controller.

        Args:
            camera: Camera controller instance
            strobe_cam: PiStrobeCam instance for ROI frame access
            config: Optional DropletDetectionConfig (uses default if None)
            config_path: Optional path to load configuration from JSON file
        """
        self.camera = camera
        self.strobe_cam = strobe_cam

        # Load configuration
        if config_path and os.path.exists(config_path):
            logger.info(f"Loading configuration from: {config_path}")
            self.config = load_config(config_path)
        else:
            self.config = config if config is not None else DropletDetectionConfig()

        # Initialize detector (will be set when ROI is available)
        self.detector: Optional[DropletDetector] = None

        # Get calibration from camera (camera-specific) or fallback to config
        camera_calibration = camera.get_calibration() if hasattr(camera, "get_calibration") else {}
        um_per_px = camera_calibration.get(
            "um_per_px", getattr(self.config, "pixel_ratio", 1.0) if self.config else 1.0
        )
        self.radius_offset_px = camera_calibration.get("radius_offset_px", 0.0)

        # Store calibration for use in measurements
        self.um_per_px = um_per_px
        unit = "um" if um_per_px != 1.0 else "px"

        # Initialize histogram with configurable window size
        histogram_window_size = getattr(self.config, "histogram_window_size", 2000)
        histogram_bins = getattr(self.config, "histogram_bins", 40)
        self.histogram = DropletHistogram(
            maxlen=histogram_window_size, bins=histogram_bins, pixel_ratio=um_per_px, unit=unit
        )

        logger.info(
            f"Droplet detector initialized with calibration: um_per_px={um_per_px}, radius_offset_px={self.radius_offset_px}"
        )

        # Threading
        self.processing_thread: Optional[threading.Thread] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)  # Prevent memory buildup
        self.running = False
        self.exit_event = threading.Event()
        self.processing_busy = False  # Flag to indicate if processing is currently busy

        # Timing instrumentation
        self.timing = TimingInstrumentation(max_samples=1000)

        # Statistics
        self.frame_count = 0
        self.droplet_count_total = 0
        self.last_update_time = time.time()

        # Processing rate tracking (for FPS display)
        self.processing_rate_hz = 0.0  # Current processing rate in Hz
        self.fps_frames_processed = 0  # Frames processed in current FPS window
        self.fps_window_start = time.time()  # Start time of current FPS window
        self.fps_update_interval = 1.0  # Update FPS every 1 second

        # Raw measurements storage for export (with timestamps)
        # Stores list of dictionaries with: timestamp_ms, frame_id, radius_px, radius_um, area_px, area_um2, x_center_px, y_center_px
        self.raw_measurements: List[Dict[str, Any]] = []
        self.max_raw_measurements = 10000  # Limit storage to prevent memory issues

    def start(self) -> bool:
        """
        Start droplet detection processing.

        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Detection already running")
            return False

        # Get ROI from camera
        roi = self.camera.get_roi()
        if roi is None:
            logger.error("ROI not set in camera. Please set ROI before starting detection.")
            return False

        # Log ROI for debugging
        logger.info(f"Starting detection with ROI: {roi}")

        # Validate ROI bounds
        x, y, width, height = roi
        if width <= 0 or height <= 0:
            logger.error(f"Invalid ROI dimensions: width={width}, height={height}")
            return False
        if x < 0 or y < 0:
            logger.error(f"Invalid ROI position: x={x}, y={y}")
            return False

        # Note: Full bounds check against camera resolution would require camera config
        # This basic validation catches obvious errors

        # Get current calibration from camera (may have changed)
        camera_calibration = (
            self.camera.get_calibration() if hasattr(self.camera, "get_calibration") else {}
        )
        um_per_px = camera_calibration.get("um_per_px", self.um_per_px)
        self.radius_offset_px = camera_calibration.get("radius_offset_px", self.radius_offset_px)

        # Update histogram with current calibration
        if um_per_px != self.histogram.pixel_ratio:
            self.histogram.pixel_ratio = um_per_px
            self.histogram.unit = "um" if um_per_px != 1.0 else "px"
            logger.info(f"Updated histogram calibration: um_per_px={um_per_px}")

        # Create detector with current calibration (including radius offset)
        self.detector = DropletDetector(roi, self.config, radius_offset_px=self.radius_offset_px)

        # Start processing thread
        self.running = True
        self.exit_event.clear()
        self.processing_thread = threading.Thread(
            target=self._processing_loop, name="DropletDetectionThread", daemon=True
        )
        self.processing_thread.start()

        logger.info("Droplet detection started")
        return True

    def stop(self) -> None:
        """Stop droplet detection processing."""
        if not self.running:
            return

        self.running = False
        self.exit_event.set()

        # Wait for thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("Droplet detection stopped")

    def _create_timing_callback(self):
        """Create timing callback for frame processing instrumentation."""

        def timing_callback(component: str, elapsed_ms: float):
            """Callback for timing instrumentation."""
            with self.timing.lock:
                if component in self.timing.timings:
                    self.timing.timings[component].append(elapsed_ms)
                    if len(self.timing.timings[component]) > self.timing.max_samples:
                        self.timing.timings[component].pop(0)

        return timing_callback

    def _process_frame_with_timing(self, frame: np.ndarray) -> List[Any]:
        """
        Process a single frame with timing instrumentation.

        Args:
            frame: ROI frame (RGB numpy array)

        Returns:
            List of droplet metrics
        """
        if self.detector is None:
            return []

        timing_callback = self._create_timing_callback()

        total_start = time.perf_counter()
        metrics = self.detector.process_frame(frame, timing_callback=timing_callback)
        total_elapsed = (time.perf_counter() - total_start) * 1000

        with self.timing.lock:
            self.timing.timings["total_per_frame"].append(total_elapsed)
            if len(self.timing.timings["total_per_frame"]) > self.timing.max_samples:
                self.timing.timings["total_per_frame"].pop(0)

        return cast(List[Any], metrics)

    def _update_histogram_with_timing(self, metrics: List) -> None:
        """
        Update histogram with timing instrumentation.

        Args:
            metrics: List of droplet metrics
        """
        histogram_start = time.perf_counter()
        self.histogram.update(metrics)
        histogram_elapsed = (time.perf_counter() - histogram_start) * 1000

        with self.timing.lock:
            self.timing.timings["histogram_update"].append(histogram_elapsed)
            if len(self.timing.timings["histogram_update"]) > self.timing.max_samples:
                self.timing.timings["histogram_update"].pop(0)

        # Store raw measurements for export
        self._store_raw_measurements(metrics)

    def _update_processing_rate(self) -> None:
        """
        Update processing rate (FPS) calculation.

        Calculates FPS over a sliding window (default 1 second).
        Updates self.processing_rate_hz with current rate.
        """
        self.fps_frames_processed += 1
        current_time = time.time()
        elapsed = current_time - self.fps_window_start

        # Update FPS every update_interval seconds
        if elapsed >= self.fps_update_interval:
            if elapsed > 0:
                self.processing_rate_hz = self.fps_frames_processed / elapsed
            else:
                self.processing_rate_hz = 0.0

            # Reset for next window
            self.fps_frames_processed = 0
            self.fps_window_start = current_time

    def _log_periodic_stats(self, frame_start_time: float) -> None:
        """
        Log periodic statistics if frame count is a multiple of 100.

        Args:
            frame_start_time: Start time for FPS calculation
        """
        if self.frame_count % 100 == 0:
            elapsed = time.time() - frame_start_time
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            logger.debug(
                f"Processed {self.frame_count} frames, "
                f"{self.droplet_count_total} droplets total, "
                f"~{fps:.1f} FPS (current rate: {self.processing_rate_hz:.2f} Hz)"
            )

    def _get_next_frame(self) -> Optional[np.ndarray]:
        """
        Get next frame from queue, handling pull-based processing.

        Returns:
            Next frame to process, or None if no frame available
        """
        if self.processing_busy:
            # Pull-based: clear queue and get only latest frame
            latest_frame = None
            while not self.frame_queue.empty():
                try:
                    latest_frame = self.frame_queue.get_nowait()
                except queue.Empty:
                    break
            return latest_frame
        else:
            # Normal processing: get frame from queue
            try:
                return self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                return None

    def _process_single_frame(self, frame: np.ndarray) -> List[Any]:
        """
        Process a single frame with error handling.

        Args:
            frame: Frame to process

        Returns:
            List of droplet metrics
        """
        if self.detector is None:
            logger.warning("Detector not initialized, skipping frame")
            return []

        # Mark as busy and process frame
        self.processing_busy = True
        try:
            # Process frame with timing
            metrics = self._process_frame_with_timing(frame)
            return metrics
        finally:
            self.processing_busy = False

    def _update_frame_statistics(self, metrics: List[Any]) -> None:
        """
        Update statistics after processing a frame.

        Args:
            metrics: List of droplet metrics
        """
        # Update histogram with timing
        self._update_histogram_with_timing(metrics)

        # Update statistics
        self.frame_count += 1
        self.droplet_count_total += len(metrics)

        # Update processing rate (FPS)
        self._update_processing_rate()

    def _processing_loop(self) -> None:
        """
        Main processing loop (runs in separate thread).

        Continuously processes frames from the queue.
        """
        logger.info("Processing loop started")

        frame_start_time = time.time()

        while self.running and not self.exit_event.is_set():
            try:
                # Get next frame
                frame = self._get_next_frame()
                if frame is None:
                    # No frames available, wait briefly
                    time.sleep(0.01)
                    continue

                # Process frame
                metrics = self._process_single_frame(frame)

                # Update statistics
                self._update_frame_statistics(metrics)

                # Log periodically
                self._log_periodic_stats(frame_start_time)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(0.01)  # Brief pause before retrying

        logger.info("Processing loop stopped")

    def add_frame(self, frame: np.ndarray) -> bool:
        """
        Add frame to processing queue.

        Called from camera thread or main thread.

        Args:
            frame: ROI frame (RGB numpy array)

        Returns:
            True if frame was added, False if queue is full or invalid
        """
        if not self.running:
            return False

        # Validate frame
        if not isinstance(frame, np.ndarray):
            logger.warning(f"Invalid frame type: {type(frame)}, expected numpy.ndarray")
            return False

        if len(frame.shape) < 2:
            logger.warning(f"Invalid frame shape: {frame.shape}")
            return False

        try:
            self.frame_queue.put_nowait(frame)
            return True
        except queue.Full:
            # Queue full - drop frame (prevent memory buildup)
            logger.debug("Frame queue full, dropping frame")
            return False

    def initialize_background(self, frames: List[np.ndarray]) -> None:
        """
        Initialize background model with multiple frames.

        Args:
            frames: List of frames (RGB numpy arrays) for background initialization
        """
        if self.detector is None:
            logger.error("Detector not initialized. Call start() first.")
            return

        logger.info(f"Initializing background with {len(frames)} frames")
        self.detector.initialize_background(frames)

    def get_histogram(self) -> Dict[str, Any]:
        """
        Get current histogram data.

        Returns:
            Dictionary with histogram and statistics (JSON-serializable)
        """
        return cast(Dict[str, Any], self.histogram.to_json())

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics.

        Returns:
            Dictionary with statistics
        """
        stats = self.histogram.get_statistics()
        stats["frame_count"] = self.frame_count
        stats["droplet_count_total"] = self.droplet_count_total
        stats["processing_rate_hz"] = round(
            self.processing_rate_hz, 2
        )  # Current processing rate in Hz

        return cast(Dict[str, Any], stats)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance timing metrics.

        Returns:
            Dictionary with timing statistics for each component
        """
        return self.timing.get_statistics()

    def update_config(self, config_dict: Dict[str, Any]) -> bool:
        """
        Update detection configuration.

        Args:
            config_dict: Dictionary of configuration values to update

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Update config
            self.config.update(config_dict)

            # Update calibration if provided
            if "pixel_ratio" in config_dict or "um_per_px" in config_dict:
                # Support both old 'pixel_ratio' and new 'um_per_px' for backward compatibility
                new_um_per_px = config_dict.get(
                    "um_per_px", config_dict.get("pixel_ratio", self.um_per_px)
                )
                self.um_per_px = new_um_per_px
                self.histogram.pixel_ratio = new_um_per_px
                self.histogram.unit = "um" if new_um_per_px != 1.0 else "px"
                logger.info(
                    f"Updated calibration: um_per_px={new_um_per_px} {self.histogram.unit}/px"
                )

            if "radius_offset_px" in config_dict:
                self.radius_offset_px = float(config_dict["radius_offset_px"])
                logger.info(f"Updated radius offset: radius_offset_px={self.radius_offset_px}")

            # Update histogram window size if changed
            if "histogram_window_size" in config_dict or "histogram_bins" in config_dict:
                new_window_size = config_dict.get(
                    "histogram_window_size", getattr(self.config, "histogram_window_size", 2000)
                )
                new_bins = config_dict.get(
                    "histogram_bins", getattr(self.config, "histogram_bins", 40)
                )
                # Note: Histogram window size change requires recreating histogram
                # This will clear existing data, so we only do it if explicitly requested
                logger.info(f"Updating histogram: window_size={new_window_size}, bins={new_bins}")
                # Recreate histogram with new parameters
                self.histogram = DropletHistogram(
                    maxlen=new_window_size,
                    bins=new_bins,
                    pixel_ratio=self.um_per_px,
                    unit=self.histogram.unit,
                )

            # Validate
            is_valid, errors = self.config.validate()
            if not is_valid:
                logger.warning(f"Configuration validation errors: {errors}")
                return False

            # Recreate detector with new config if running
            if self.running and self.detector is not None:
                roi = self.camera.get_roi()
                if roi:
                    # Recreate detector with updated config and offset
                    self.detector = DropletDetector(
                        roi, self.config, radius_offset_px=self.radius_offset_px
                    )
                    logger.info("Detector recreated with updated configuration")

            return True
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False

    def load_profile(self, profile_path: str) -> bool:
        """
        Load configuration profile from JSON file.

        Args:
            profile_path: Path to JSON configuration file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            self.config = load_config(profile_path)

            # Update calibration from loaded config
            if hasattr(self.config, "pixel_ratio"):
                pixel_ratio = getattr(self.config, "pixel_ratio", 1.0)
                if pixel_ratio != 1.0:
                    self.um_per_px = pixel_ratio
                    self.histogram.pixel_ratio = pixel_ratio
                    self.histogram.unit = "um"

            # Recreate detector with new config if running
            if self.running and self.detector is not None:
                roi = self.camera.get_roi()
                if roi:
                    # Get current calibration (may have changed)
                    camera_calibration = (
                        self.camera.get_calibration()
                        if hasattr(self.camera, "get_calibration")
                        else {}
                    )
                    camera_um_per_px = camera_calibration.get("um_per_px", self.um_per_px)
                    radius_offset_px = camera_calibration.get(
                        "radius_offset_px", self.radius_offset_px
                    )
                    # Use camera calibration if available, otherwise keep existing
                    if camera_um_per_px != self.um_per_px:
                        self.um_per_px = camera_um_per_px
                        self.histogram.pixel_ratio = camera_um_per_px
                        self.histogram.unit = "um" if camera_um_per_px != 1.0 else "px"
                    self.detector = DropletDetector(
                        roi, self.config, radius_offset_px=radius_offset_px
                    )
                    logger.info(f"Profile loaded: {profile_path}")

            return True
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            return False

    def save_profile(
        self, profile_path: str, nested: bool = False, include_modules: bool = False
    ) -> bool:
        """
        Save current configuration to JSON file.

        Args:
            profile_path: Path to save JSON configuration file
            nested: If True, save in nested structure. If False, save flat (default, backward compatible)
            include_modules: If True and nested=True, include modules section

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            save_config(self.config, profile_path, nested=nested, include_modules=include_modules)
            format_type = "nested" if nested else "flat"
            logger.info(f"Profile saved ({format_type} format): {profile_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False

    def reset(self) -> None:
        """Reset detector state and statistics."""
        if self.detector:
            self.detector.reset()
        self.histogram.clear()
        self.timing.reset()
        self.frame_count = 0
        self.droplet_count_total = 0
        self.last_update_time = time.time()

        # Reset processing rate tracking
        self.processing_rate_hz = 0.0
        self.fps_frames_processed = 0
        self.fps_window_start = time.time()

        # Clear raw measurements
        self.raw_measurements.clear()

        logger.info("Detector reset")

    def _store_raw_measurements(self, metrics: List[Any]) -> None:
        """
        Store raw droplet measurements with timestamps for export.

        Args:
            metrics: List of DropletMetrics objects
        """
        if not metrics:
            return

        timestamp_ms = int(time.time() * 1000)  # Milliseconds since epoch
        frame_id = self.frame_count

        for metric in metrics:
            # Calculate radius from equivalent diameter
            radius_px = metric.equivalent_diameter / 2.0
            radius_um = radius_px * self.um_per_px

            # Calculate area in um²
            area_um2 = metric.area * (self.um_per_px**2)

            measurement = {
                "timestamp_ms": timestamp_ms,
                "frame_id": frame_id,
                "radius_px": round(radius_px, 2),
                "radius_um": round(radius_um, 2),
                "area_px": round(metric.area, 2),
                "area_um2": round(area_um2, 2),
                "x_center_px": round(metric.centroid[0], 2),
                "y_center_px": round(metric.centroid[1], 2),
                "major_axis_px": round(metric.major_axis, 2),
                "major_axis_um": round(metric.major_axis * self.um_per_px, 2),
                "equivalent_diameter_px": round(metric.equivalent_diameter, 2),
                "equivalent_diameter_um": round(metric.equivalent_diameter * self.um_per_px, 2),
            }

            self.raw_measurements.append(measurement)

            # Limit storage to prevent memory issues
            if len(self.raw_measurements) > self.max_raw_measurements:
                # Remove oldest measurements (keep most recent)
                self.raw_measurements = self.raw_measurements[-self.max_raw_measurements :]

    def export_data(self, format_type: str = "csv") -> Optional[str]:
        """
        Export raw droplet measurements to CSV or TXT format.

        Args:
            format_type: Export format ("csv" or "txt")

        Returns:
            String content of exported file, or None if no data
        """
        if not self.raw_measurements:
            return None

        import csv
        import io

        output = io.StringIO()

        # Define column headers
        headers = [
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

        if format_type.lower() == "csv":
            # CSV format
            writer = csv.writer(output)
            writer.writerow(headers)

            for measurement in self.raw_measurements:
                row = [measurement.get(header, "") for header in headers]
                writer.writerow(row)

        elif format_type.lower() == "txt":
            # Tab-separated text format
            output.write("\t".join(headers) + "\n")

            for measurement in self.raw_measurements:
                row = [str(measurement.get(header, "")) for header in headers]
                output.write("\t".join(row) + "\n")

        else:
            raise ValueError(f"Unsupported format: {format_type}. Use 'csv' or 'txt'")

        return output.getvalue()
