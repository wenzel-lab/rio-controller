"""
Main droplet detector orchestrator.

Integrates all modules into a unified detection pipeline.
"""

import logging
import time
import numpy as np
import cv2
from typing import List, Optional, Tuple, Callable

from .config import DropletDetectionConfig
from .preprocessor import Preprocessor
from .segmenter import Segmenter
from .measurer import Measurer, DropletMetrics
from .artifact_rejector import ArtifactRejector
from .utils import ensure_grayscale

logger = logging.getLogger(__name__)


class DropletDetector:
    """
    Main droplet detection orchestrator.

    Integrates preprocessing, segmentation, measurement, and artifact rejection
    into a unified pipeline. Designed to work with existing BaseCamera abstraction.
    """

    def __init__(
        self,
        roi: Tuple[int, int, int, int],
        config: Optional[DropletDetectionConfig] = None,
        radius_offset_px: float = 0.0,
    ):
        """
        Initialize droplet detector.

        Args:
            roi: Region of interest (x, y, width, height)
            config: DropletDetectionConfig instance (uses default if None)
            radius_offset_px: Pixel offset to correct for threshold bias (default: 0.0)
        """
        self.roi = roi
        self.config = config if config is not None else DropletDetectionConfig()
        self.radius_offset_px = radius_offset_px

        # Initialize modules
        self.preprocessor = Preprocessor(self.config)
        self.segmenter = Segmenter(self.config)
        self.measurer = Measurer(self.config)
        self.artifact_rejector = ArtifactRejector(self.config)

        # State tracking
        self.prev_centroids: List[Tuple[float, float]] = []
        self.frame_count = 0
        self.background_initialized = False

    def initialize_background(self, frames: List[np.ndarray]) -> None:
        """
        Initialize background model with multiple frames.

        Args:
            frames: List of frames (RGB numpy arrays) for background initialization
        """
        logger.info(f"Initializing background with {len(frames)} frames")
        for frame in frames:
            self.preprocessor.initialize_background(frame)
        self.background_initialized = self.preprocessor.background_initialized

    def process_frame(
        self, frame: np.ndarray, timing_callback: Optional[Callable[[str, float], None]] = None
    ) -> List[DropletMetrics]:
        """
        Process a single ROI frame and return detected droplets.

        Pipeline:
        1. Preprocess (background correction, thresholding, morphology)
        2. Segment (contour detection, filtering)
        3. Filter artifacts (temporal filtering, motion validation)
        4. Measure (geometric metrics)

        Args:
            frame: ROI frame from camera.get_frame_roi() (RGB numpy array)
            timing_callback: Optional callback function(component_name, elapsed_ms)
                            for timing instrumentation

        Returns:
            List of DropletMetrics objects
        """
        self.frame_count += 1

        # Validate frame
        if not isinstance(frame, np.ndarray):
            logger.error(f"Frame is not a numpy array (type: {type(frame)})")
            return []

        if len(frame.shape) < 2:
            logger.error(f"Invalid frame shape: {frame.shape}")
            return []

        try:
            # 1. Preprocess
            try:
                if timing_callback:
                    start = time.perf_counter()
                    mask = self.preprocessor.process(frame)
                    elapsed = (time.perf_counter() - start) * 1000
                    timing_callback("preprocessing", elapsed)
                else:
                    mask = self.preprocessor.process(frame)
            except cv2.error as e:
                # Handle size mismatch errors (ROI changed)
                if "Sizes of input arguments do not match" in str(e):
                    logger.warning(f"Frame size mismatch detected, resetting background: {e}")
                    self.preprocessor.reset_background()
                    # Return empty list for this frame, background will reinitialize
                    return []
                raise

            # If background not initialized yet, return empty list
            if not self.preprocessor.background_initialized:
                if self.frame_count <= self.config.background_frames:
                    # Still initializing background
                    self.preprocessor.initialize_background(frame)
                    if self.frame_count % 10 == 0:  # Log every 10 frames during initialization
                        logger.debug(
                            f"Initializing background: frame {self.frame_count}/{self.config.background_frames}"
                        )
                return []

            # 2. Segment
            if timing_callback:
                start = time.perf_counter()

            # Extract channel band from ROI (assume channel is in middle of ROI)
            roi_y = self.roi[1]
            roi_height = self.roi[3]
            channel_band = (roi_y, roi_y + roi_height)

            contours = self.segmenter.detect_contours(mask, channel_band=channel_band)

            if timing_callback:
                elapsed = (time.perf_counter() - start) * 1000
                timing_callback("segmentation", elapsed)

            if not contours:
                # Don't log - too verbose
                return []

            # 3. Filter artifacts (temporal filtering)
            if timing_callback:
                start = time.perf_counter()

            if self.config.use_frame_diff:
                gray = ensure_grayscale(frame)
                moving_contours = self.artifact_rejector.filter_with_frame_diff(contours, gray)
            else:
                moving_contours = self.artifact_rejector.filter(contours, self.prev_centroids)

            if timing_callback:
                elapsed = (time.perf_counter() - start) * 1000
                timing_callback("artifact_rejection", elapsed)

            if not moving_contours:
                # Don't log - too verbose
                return []

            # 4. Measure
            if timing_callback:
                start = time.perf_counter()

            metrics = self.measurer.measure(moving_contours, radius_offset_px=self.radius_offset_px)

            if timing_callback:
                elapsed = (time.perf_counter() - start) * 1000
                timing_callback("measurement", elapsed)

            # Update state for next frame
            self.prev_centroids = [m.centroid for m in metrics]

            # Don't log every frame - too verbose
            # Logging will be done at histogram refresh intervals in web controller

            return metrics

        except Exception as e:
            logger.error(
                f"Error processing frame {self.frame_count} (ROI: {self.roi}): {e}", exc_info=True
            )
            return []

    def reset(self) -> None:
        """Reset detector state (for re-initialization)."""
        self.preprocessor.reset_background()
        self.artifact_rejector.reset()
        self.prev_centroids = []
        self.frame_count = 0
        self.background_initialized = False
        logger.debug("Droplet detector reset")
