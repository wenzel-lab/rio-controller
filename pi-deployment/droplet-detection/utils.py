"""
Utility functions for droplet detection module.
"""

import numpy as np
import cv2
from typing import Tuple


def ensure_grayscale(frame: np.ndarray) -> np.ndarray:
    """
    Convert frame to grayscale if needed.

    Args:
        frame: Input frame (RGB, BGR, or grayscale)

    Returns:
        Grayscale frame
    """
    if len(frame.shape) == 3:
        # Assume RGB if 3 channels
        return cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    elif len(frame.shape) == 2:
        return frame
    else:
        raise ValueError(f"Unexpected frame shape: {frame.shape}")


def calculate_aspect_ratio(contour: np.ndarray) -> float:
    """
    Calculate aspect ratio of a contour.

    Args:
        contour: Contour array from cv2.findContours

    Returns:
        Aspect ratio (max dimension / min dimension)
    """
    x, y, w, h = cv2.boundingRect(contour)
    if min(w, h) == 0:
        return float("inf")
    return max(w, h) / min(w, h)


def get_contour_centroid(contour: np.ndarray) -> Tuple[float, float]:
    """
    Calculate centroid of a contour.

    Args:
        contour: Contour array from cv2.findContours

    Returns:
        Tuple of (cx, cy) centroid coordinates
    """
    M = cv2.moments(contour)
    if M["m00"] == 0:
        return (0.0, 0.0)
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return (cx, cy)


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Calculate Euclidean distance between two points.

    Args:
        p1: First point (x, y)
        p2: Second point (x, y)

    Returns:
        Euclidean distance
    """
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
