"""
Preprocessing module for droplet detection.

Handles background correction, thresholding, and morphological operations.
"""

import logging
import numpy as np
import cv2
from typing import Optional, Tuple
from collections import deque

from .config import DropletDetectionConfig
from .utils import ensure_grayscale

logger = logging.getLogger(__name__)


class Preprocessor:
    """
    Preprocessing module for droplet detection.

    Implements:
    - Grayscale conversion
    - Background correction (static or high-pass filtering)
    - Thresholding (Otsu or adaptive)
    - Morphological operations (noise removal, hole filling)
    """

    def __init__(self, config: DropletDetectionConfig):
        """
        Initialize preprocessor with configuration.

        Args:
            config: DropletDetectionConfig instance
        """
        self.config = config
        self.background: Optional[np.ndarray] = None
        self.background_frames: deque = deque(maxlen=config.background_frames)
        self.background_initialized: bool = False
        self.background_shape: Optional[Tuple[int, int]] = None  # Track background size (height, width)

    def initialize_background(self, frame: np.ndarray) -> None:
        """
        Initialize background model with a frame.

        For static background method, collects frames and computes median.
        For high-pass method, this is a no-op (background computed per-frame).

        Args:
            frame: Input frame (RGB or grayscale)
        """
        if self.config.background_method == "static":
            gray = ensure_grayscale(frame)
            
            # Check if frame size changed (ROI changed)
            current_shape: Tuple[int, int] = gray.shape[:2]  # (height, width)
            if self.background_shape is not None and self.background_shape != current_shape:
                logger.warning(
                    f"Frame size changed from {self.background_shape} to {current_shape}, resetting background"
                )
                self.reset_background()
            
            # Store shape for future comparisons
            if self.background_shape is None:
                self.background_shape = current_shape
            
            self.background_frames.append(gray.copy())

            # Compute median when we have enough frames
            if len(self.background_frames) >= self.config.background_frames:
                frames_array = np.array(list(self.background_frames))
                self.background = np.median(frames_array, axis=0).astype(np.uint8)
                self.background_initialized = True
                logger.info(f"Background initialized with {len(self.background_frames)} frames, shape: {self.background_shape}")
        # For high-pass method, no initialization needed

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Process frame through preprocessing pipeline.

        Pipeline:
        1. Grayscale conversion
        2. Background correction
        3. Thresholding
        4. Morphological operations

        Args:
            frame: Input frame (RGB numpy array)

        Returns:
            Binary mask (uint8, 0 or 255)
        """
        # Validate frame
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"Frame must be numpy array, got {type(frame)}")
        if len(frame.shape) < 2:
            raise ValueError(f"Invalid frame shape: {frame.shape}")

        # 1. Grayscale conversion
        gray = ensure_grayscale(frame)

        # 2. Background correction
        if self.config.background_method == "static":
            if not self.background_initialized:
                # Still collecting background frames
                self.initialize_background(frame)
                # Return empty mask while initializing
                return np.zeros_like(gray, dtype=np.uint8)

            # Check if background size matches current frame size
            if self.background is not None and self.background.shape != gray.shape:
                logger.warning(
                    f"Background shape {self.background.shape} doesn't match frame shape {gray.shape}, resetting"
                )
                self.reset_background()
                self.initialize_background(frame)
                return np.zeros_like(gray, dtype=np.uint8)

            # Static background subtraction
            if self.background is None:
                # Background not ready yet
                return np.zeros_like(gray, dtype=np.uint8)
            
            gray_corr = cv2.absdiff(gray, self.background)

        elif self.config.background_method == "highpass":
            # High-pass filtering (subtract blurred version)
            blur = cv2.GaussianBlur(gray, self.config.gaussian_blur_kernel, 0)
            gray_corr = cv2.subtract(gray, blur)
            # Ensure non-negative
            gray_corr = np.maximum(gray_corr, 0)
        else:
            # No background correction
            gray_corr = gray

        # Optional: Intensity normalization
        # Clip to [0, 255] range
        gray_corr = np.clip(gray_corr, 0, 255).astype(np.uint8)

        # 3. Thresholding
        if self.config.threshold_method == "otsu":
            _, mask = cv2.threshold(gray_corr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif self.config.threshold_method == "adaptive":
            mask = cv2.adaptiveThreshold(
                gray_corr,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                self.config.adaptive_block_size,
                self.config.adaptive_C,
            )
        else:
            raise ValueError(f"Unknown threshold method: {self.config.threshold_method}")

        # 4. Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.config.morph_kernel_size)

        if self.config.morph_operation == "open":
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        elif self.config.morph_operation == "close":
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        elif self.config.morph_operation == "both":
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        # else: no morphological operation

        return mask

    def reset_background(self) -> None:
        """Reset background model (for re-initialization)."""
        self.background = None
        self.background_frames.clear()
        self.background_initialized = False
        self.background_shape = None
        logger.debug("Background model reset")
