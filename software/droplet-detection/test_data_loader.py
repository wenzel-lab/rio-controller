"""
Test data loader for droplet detection.

Loads test images from droplet_AInalysis repository for testing and validation.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple


def find_test_images(base_path: Optional[str] = None) -> List[str]:
    """
    Find test images from droplet_AInalysis repository.

    Args:
        base_path: Base path to droplet_AInalysis repository.
                  If None, tries to find it relative to current directory.

    Returns:
        List of image file paths
    """
    if base_path is None:
        # Try to find droplet_AInalysis relative to open-microfluidics-workstation
        current_dir = Path(__file__).parent.parent.parent.parent
        base_path = current_dir / "droplet_AInalysis"

    base_path = Path(base_path)
    test_dir = base_path / "imgs" / "real_imgs"

    if not test_dir.exists():
        # Try alternative location
        test_dir = base_path / "imgs"
        if not test_dir.exists():
            return []

    # Find all image files
    image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
    image_files = []

    for ext in image_extensions:
        image_files.extend(list(test_dir.glob(f"*{ext}")))
        image_files.extend(list(test_dir.glob(f"*{ext.upper()}")))

    # Sort and return as strings
    return sorted([str(f) for f in image_files])


def load_test_image(image_path: str) -> np.ndarray:
    """
    Load a test image.

    Args:
        image_path: Path to image file

    Returns:
        Image as RGB numpy array
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img_rgb


def extract_roi_from_image(
    image: np.ndarray, roi: Optional[Tuple[int, int, int, int]] = None
) -> np.ndarray:
    """
    Extract ROI from image.

    Args:
        image: Full image (RGB numpy array)
        roi: Optional ROI tuple (x, y, width, height).
             If None, returns full image.

    Returns:
        ROI image (RGB numpy array)
    """
    if roi is None:
        return image

    x, y, w, h = roi
    return image[y : y + h, x : x + w]


def get_default_roi_for_test_image(image: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Get a default ROI for testing (assumes channel is in center of image).

    Args:
        image: Full image (RGB numpy array)

    Returns:
        ROI tuple (x, y, width, height)
    """
    h, w = image.shape[:2]

    # Default: center 50% of width, 20% of height
    roi_width = int(w * 0.5)
    roi_height = int(h * 0.2)
    roi_x = (w - roi_width) // 2
    roi_y = (h - roi_height) // 2

    return (roi_x, roi_y, roi_width, roi_height)
