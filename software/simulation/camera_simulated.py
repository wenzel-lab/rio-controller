"""
Simulated camera implementation.

Generates synthetic frames with optional droplet patterns for testing without
physical hardware. This module provides a drop-in replacement for real camera
implementations, allowing the application to run and be tested on any system.

Classes:
    SimulatedCamera: Camera implementation that generates synthetic frames
"""

import time
import logging
import os
from typing import Optional, Callable, Tuple, List
from threading import Event, Thread
from pathlib import Path

# Try to import numpy and cv2 - required for camera simulation
try:
    import numpy as np
    import cv2
except ImportError as e:
    raise ImportError(
        f"Camera simulation requires numpy and opencv-python. "
        f"Install with: pip install numpy opencv-python. Error: {e}"
    )

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 30
DEFAULT_DROPLET_COUNT = 5  # Active droplets at once (will be replenished)
DEFAULT_DROPLET_SIZE_RANGE = (15, 45)  # More realistic size range
DEFAULT_DROPLET_SPAWN_RATE = (
    0.3  # Probability of spawning new droplet per frame (higher for continuous flow)
)
JPEG_QUALITY = 85
FRAME_WAIT_TIME_S = 0.1

_SCRIPT_DIR = Path(__file__).parent.resolve()


def _resolve_droplet_dataset_base(
    env_value: Optional[str] = None, repo_root: Optional[Path] = None
) -> Optional[Path]:
    """
    Resolve the base path for droplet sample data.

    Priority:
    1) Env var RIO_DROPLET_TESTDATA_DIR (if set and exists)
    2) Repo-relative fallback: <repo>/software/tests/data/droplet (if exists)
    3) None (will trigger synthetic backgrounds/droplets)
    """

    env_path = env_value if env_value is not None else os.getenv("RIO_DROPLET_TESTDATA_DIR")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.exists():
            return candidate

    root = repo_root if repo_root is not None else _SCRIPT_DIR.parent.parent
    fallback = root / "software" / "tests" / "data" / "droplet"
    if fallback.exists():
        return fallback

    return None


_DROPLET_ANALYSIS_PATH = None
_BACKGROUNDS_PATH = None
_DROPLETS_PATH = None

_DATASET_BASE = _resolve_droplet_dataset_base()
if _DATASET_BASE:
    _DROPLET_ANALYSIS_PATH = _DATASET_BASE
    _BACKGROUNDS_PATH = _DATASET_BASE / "backgrounds"
    _DROPLETS_PATH = _DATASET_BASE / "droplets"

# Try to import real camera classes (will fail on non-Pi systems, that's OK)
try:
    from drivers.camera.camera_base import BaseCamera
except ImportError:
    # Fallback for when camera_base not available
    from abc import ABC, abstractmethod

    class BaseCamera(ABC):  # type: ignore[no-redef]
        @abstractmethod
        def start(self):
            pass

        @abstractmethod
        def stop(self):
            pass

        @abstractmethod
        def get_frame_array(self):
            pass

        @abstractmethod
        def get_frame_roi(self, roi_coords):
            pass

        @abstractmethod
        def set_config(self, config):
            pass

        @abstractmethod
        def set_frame_callback(self, callback):
            pass


class SimulatedCamera(BaseCamera):
    """
    Simulated camera that generates synthetic frames.

    Features:
    - Generates test frames at configurable FPS
    - Optional droplet patterns (circles) for testing detection
    - Supports ROI cropping
    - Frame callbacks for strobe integration
    - JPEG encoding for web streaming
    """

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        fps: int = DEFAULT_FPS,
        generate_droplets: bool = True,
        droplet_count: int = DEFAULT_DROPLET_COUNT,
        droplet_size_range: Tuple[int, int] = DEFAULT_DROPLET_SIZE_RANGE,
    ):
        """
        Initialize simulated camera.

        Args:
            width: Frame width in pixels (default: 640)
            height: Frame height in pixels (default: 480)
            fps: Target frames per second (default: 30)
            generate_droplets: Whether to draw synthetic droplets (default: True)
            droplet_count: Number of droplets per frame (default: 5)
            droplet_size_range: (min, max) droplet radius in pixels (default: (10, 50))

        Raises:
            ValueError: If width, height, or fps are invalid
        """
        # Validate inputs
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid dimensions: {width}x{height}")
        if fps <= 0:
            raise ValueError(f"Invalid FPS: {fps}")
        if droplet_count < 0:
            raise ValueError(f"Invalid droplet count: {droplet_count}")

        logger.debug(
            f"Initializing SimulatedCamera: {width}x{height} @ {fps}fps, droplets={generate_droplets}"
        )
        self.config = {
            "size": [width, height],
            "FrameRate": fps,
            "ShutterSpeed": int(1000000 / fps),  # microseconds
        }

        self.width = width
        self.height = height
        self.fps = fps
        self.generate_droplets = generate_droplets
        self.droplet_count = droplet_count
        self.droplet_size_range = droplet_size_range
        self.droplet_spawn_rate = DEFAULT_DROPLET_SPAWN_RATE

        self.cam_running_event = Event()
        self.frame_callback: Optional[Callable[[], None]] = None
        self.current_frame: Optional[np.ndarray] = None
        self.frame_thread: Optional[Thread] = None

        # Load real background and droplet images
        self.background_image: Optional[np.ndarray] = None
        self.droplet_templates: List[np.ndarray] = []
        self._load_real_images()

        # For droplet animation
        self.frame_counter = 0
        self.droplet_positions: list[tuple[float, float]] = []
        self.droplet_velocities: list[tuple[float, float]] = []
        self.droplet_sizes: list[float] = []  # Store radius for each droplet
        self.droplet_aspect_ratios: list[float] = (
            []
        )  # Store aspect ratio (1.0 = round, >1.0 = elliptical)
        self.droplet_templates_idx: list[int] = []  # Which template to use for each droplet
        self.droplet_intensities: list[float] = []  # Intensity multiplier (for contrast variation)
        self._initialize_droplets()

    def _load_real_images(self) -> None:
        """Load real background and droplet images from test dataset."""
        # Load background image
        if _BACKGROUNDS_PATH and _BACKGROUNDS_PATH.exists():
            bg_files = list(_BACKGROUNDS_PATH.glob("*.jpg"))
            if bg_files:
                bg_path = bg_files[0]  # Use first available background
                bg_img = cv2.imread(str(bg_path))
                if bg_img is not None:
                    # Resize to match camera dimensions
                    self.background_image = cv2.resize(bg_img, (self.width, self.height))
                    logger.info(f"Loaded real background: {bg_path.name}")
                else:
                    logger.warning(f"Failed to load background: {bg_path}")
            else:
                logger.warning("No background images found, using synthetic background")
        else:
            logger.warning("Background path not found, using synthetic background")

        # Load droplet templates (load more for variety)
        if _DROPLETS_PATH and _DROPLETS_PATH.exists():
            droplet_files = list(_DROPLETS_PATH.glob("*.png"))
            for droplet_path in droplet_files[:20]:  # Load up to 20 templates for variety
                droplet_img = cv2.imread(str(droplet_path), cv2.IMREAD_UNCHANGED)
                if droplet_img is not None:
                    # Convert RGBA to BGR if needed
                    if droplet_img.shape[2] == 4:
                        # Extract alpha channel (keep as uint8, normalize later)
                        alpha = droplet_img[:, :, 3]  # 2D array (height, width)
                        rgb = droplet_img[:, :, :3]  # BGR from RGBA
                        # Create BGR image with transparency
                        self.droplet_templates.append((rgb, alpha))
                    else:
                        self.droplet_templates.append((droplet_img, None))
                    logger.debug(f"Loaded droplet template: {droplet_path.name}")

            if self.droplet_templates:
                logger.info(f"Loaded {len(self.droplet_templates)} real droplet templates")
            else:
                logger.warning("No droplet templates loaded, will use synthetic droplets")
        else:
            logger.warning("Droplet path not found, using synthetic droplets")

    def _create_new_droplet(self, enter_from_edge: bool = False) -> dict:
        """Create a new droplet with Gaussian-distributed parameters."""
        # Gaussian distribution for droplet size (radius)
        # Mean: middle of range, Std: 1/3 of range
        mean_radius = (self.droplet_size_range[0] + self.droplet_size_range[1]) / 2.0
        std_radius = (self.droplet_size_range[1] - self.droplet_size_range[0]) / 6.0
        radius = float(np.random.normal(mean_radius, std_radius))
        radius = np.clip(radius, self.droplet_size_range[0], self.droplet_size_range[1])

        # Gaussian distribution for aspect ratio: mostly round (mean=1.0), some elliptical
        if np.random.random() < 0.7:  # 70% round
            aspect_ratio = float(np.random.normal(1.0, 0.1))  # Mean=1.0, Std=0.1
            aspect_ratio = np.clip(aspect_ratio, 0.8, 1.2)
        else:  # 30% elliptical
            aspect_ratio = float(np.random.normal(1.5, 0.3))  # Mean=1.5, Std=0.3
            aspect_ratio = np.clip(aspect_ratio, 1.2, 2.5)

        # Select droplet template (if available)
        if self.droplet_templates:
            template_idx = np.random.randint(0, len(self.droplet_templates))
        else:
            template_idx = -1  # Use synthetic

        # Gaussian distribution for intensity (contrast variation)
        # Mean: 0.6 (less contrast), Std: 0.15
        intensity = float(np.random.normal(0.6, 0.15))
        intensity = np.clip(intensity, 0.3, 0.9)  # Range: 30-90% of max brightness

        # Position: either enter from edge or random
        if enter_from_edge:
            # Enter from random edge
            edge = np.random.randint(0, 4)  # 0=top, 1=right, 2=bottom, 3=left
            if edge == 0:  # Top
                x = float(np.random.uniform(radius, self.width - radius))
                y = float(-radius - 5)  # Start off-screen
                angle = float(np.random.uniform(np.pi / 4, 3 * np.pi / 4))  # Downward
            elif edge == 1:  # Right
                x = float(self.width + radius + 5)
                y = float(np.random.uniform(radius, self.height - radius))
                angle = float(np.random.uniform(3 * np.pi / 4, 5 * np.pi / 4))  # Leftward
            elif edge == 2:  # Bottom
                x = float(np.random.uniform(radius, self.width - radius))
                y = float(self.height + radius + 5)
                angle = float(np.random.uniform(5 * np.pi / 4, 7 * np.pi / 4))  # Upward
            else:  # Left
                x = float(-radius - 5)
                y = float(np.random.uniform(radius, self.height - radius))
                angle = float(np.random.uniform(-np.pi / 4, np.pi / 4))  # Rightward
        else:
            # Random position
            x = float(np.random.uniform(radius, self.width - radius))
            y = float(np.random.uniform(radius, self.height - radius))
            angle = float(np.random.uniform(0, 2 * np.pi))

        # Gaussian distribution for velocity (MUCH faster - 5-10x faster)
        # Mean: 20 px/frame, Std: 6 px/frame (range roughly 8-35 px/frame)
        speed = float(np.random.normal(20.0, 6.0))
        speed = np.clip(speed, 10.0, 35.0)  # Minimum 10, maximum 35 pixels per frame
        vx = speed * np.cos(angle)
        vy = speed * np.sin(angle)

        return {
            "pos": (x, y),
            "vel": (vx, vy),
            "radius": radius,
            "aspect_ratio": aspect_ratio,
            "template_idx": template_idx,
            "intensity": intensity,
        }

    def _initialize_droplets(self) -> None:
        """Initialize droplets - start with empty list, they'll spawn from edges."""
        self.droplet_positions = []
        self.droplet_velocities = []
        self.droplet_sizes = []
        self.droplet_aspect_ratios = []
        self.droplet_templates_idx = []
        self.droplet_intensities = []

        # Spawn initial droplets
        for _ in range(self.droplet_count):
            droplet = self._create_new_droplet(enter_from_edge=True)
            self.droplet_positions.append(droplet["pos"])
            self.droplet_velocities.append(droplet["vel"])
            self.droplet_sizes.append(droplet["radius"])
            self.droplet_aspect_ratios.append(droplet["aspect_ratio"])
            self.droplet_templates_idx.append(droplet["template_idx"])
            self.droplet_intensities.append(droplet["intensity"])

    def _generate_frame(self) -> np.ndarray:
        """
        Generate a synthetic frame with real background and realistic droplets.

        Returns:
            numpy array (BGR format for OpenCV compatibility)
        """
        # Use real background if available, otherwise synthetic
        # Optimize: reuse background, only copy when needed
        if self.background_image is not None:
            # Copy background (required since we'll modify it)
            frame = self.background_image.copy()
        else:
            # Create base frame (dark background, typical for microfluidics)
            # Reuse if same size, otherwise create new
            if not hasattr(self, "_synthetic_bg") or self._synthetic_bg.shape != (
                self.height,
                self.width,
                3,
            ):
                self._synthetic_bg = np.full(
                    (self.height, self.width, 3), (20, 20, 20), dtype=np.uint8
                )
            frame = self._synthetic_bg.copy()

        if self.generate_droplets:
            # Remove droplets that left the frame (optimized: iterate backwards)
            droplets_to_remove = []
            for i in range(len(self.droplet_positions) - 1, -1, -1):
                # Safeguard against length mismatches
                if i >= len(self.droplet_sizes):
                    continue
                pos = self.droplet_positions[i]
                radius = self.droplet_sizes[i]
                # Check if completely outside frame (with margin)
                margin = radius + 10
                if (
                    pos[0] < -margin
                    or pos[0] > self.width + margin
                    or pos[1] < -margin
                    or pos[1] > self.height + margin
                ):
                    droplets_to_remove.append(i)

            # Remove in reverse order to maintain indices
            for i in droplets_to_remove:
                del self.droplet_positions[i]
                del self.droplet_velocities[i]
                del self.droplet_sizes[i]
                del self.droplet_aspect_ratios[i]
                del self.droplet_templates_idx[i]
                del self.droplet_intensities[i]

            # Spawn new droplets from edges (to maintain count)
            # Higher spawn rate for continuous flow
            while len(self.droplet_positions) < self.droplet_count:
                if np.random.random() < self.droplet_spawn_rate:
                    droplet = self._create_new_droplet(enter_from_edge=True)
                    self.droplet_positions.append(droplet["pos"])
                    self.droplet_velocities.append(droplet["vel"])
                    self.droplet_sizes.append(droplet["radius"])
                    self.droplet_aspect_ratios.append(droplet["aspect_ratio"])
                    self.droplet_templates_idx.append(droplet["template_idx"])
                    self.droplet_intensities.append(droplet["intensity"])
                else:
                    break  # Don't force spawn every frame

            # Ensure all droplet arrays stay in sync (defensive against length mismatches)
            n = min(
                len(self.droplet_positions),
                len(self.droplet_velocities),
                len(self.droplet_sizes),
                len(self.droplet_aspect_ratios),
                len(self.droplet_templates_idx),
                len(self.droplet_intensities),
            )
            if n < len(self.droplet_positions):
                self.droplet_positions = self.droplet_positions[:n]
            if n < len(self.droplet_velocities):
                self.droplet_velocities = self.droplet_velocities[:n]
            if n < len(self.droplet_sizes):
                self.droplet_sizes = self.droplet_sizes[:n]
            if n < len(self.droplet_aspect_ratios):
                self.droplet_aspect_ratios = self.droplet_aspect_ratios[:n]
            if n < len(self.droplet_templates_idx):
                self.droplet_templates_idx = self.droplet_templates_idx[:n]
            if n < len(self.droplet_intensities):
                self.droplet_intensities = self.droplet_intensities[:n]

            # Update droplet positions (no collision detection for performance)
            for i in range(n):
                pos = self.droplet_positions[i]
                vel = self.droplet_velocities[i]
                radius = self.droplet_sizes[i]

                # Simple position update (no collision, no bouncing)
                new_x = pos[0] + vel[0]
                new_y = pos[1] + vel[1]

                # Update position
                self.droplet_positions[i] = (new_x, new_y)

                # Draw droplet (only if visible in frame)
                if (
                    -radius <= new_x <= self.width + radius
                    and -radius <= new_y <= self.height + radius
                ):
                    template_idx = self.droplet_templates_idx[i]
                    intensity = self.droplet_intensities[i]
                    aspect_ratio = self.droplet_aspect_ratios[i]

                    if template_idx >= 0 and template_idx < len(self.droplet_templates):
                        # Use real droplet template
                        template, alpha = self.droplet_templates[template_idx]
                        self._draw_real_droplet(
                            frame, [new_x, new_y], radius, aspect_ratio, template, alpha, intensity
                        )
                    else:
                        # Use synthetic droplet (less contrast)
                        self._draw_synthetic_droplet(
                            frame, [new_x, new_y], radius, aspect_ratio, intensity
                        )

        # Add realistic sensor noise (Gaussian distribution) - optimized
        # Mean: 0, Std: 3 (more realistic than uniform)
        # Use in-place operations for better performance
        frame_float = frame.astype(np.float32)
        noise = np.random.normal(0, 3, frame.shape).astype(np.float32)
        np.clip(frame_float + noise, 0, 255, out=frame_float)
        frame = frame_float.astype(np.uint8)

        self.frame_counter += 1
        return frame

    def _draw_real_droplet(
        self,
        frame: np.ndarray,
        pos: List[float],
        radius: float,
        aspect_ratio: float,
        template: np.ndarray,
        alpha: Optional[np.ndarray],
        intensity: float,
    ) -> None:
        """Draw a droplet using a real template image (optimized for performance)."""
        # Calculate size for template
        template_h, template_w = template.shape[:2]
        scale = (2 * radius) / max(template_w, template_h)

        # Apply aspect ratio scaling
        if aspect_ratio >= 1.0:
            new_w = int(template_w * scale * aspect_ratio)
            new_h = int(template_h * scale)
        else:
            new_w = int(template_w * scale)
            new_h = int(template_h * scale / aspect_ratio)

        # Skip if too small
        if new_w <= 0 or new_h <= 0:
            return

        # Resize template (use faster interpolation for performance)
        resized_template = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Apply intensity (contrast reduction) - in-place for performance
        resized_template = (resized_template * intensity).astype(np.uint8)

        # Calculate position (top-left corner)
        x = int(pos[0] - new_w // 2)
        y = int(pos[1] - new_h // 2)

        # Clamp to frame bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(frame.shape[1], x + new_w)
        y2 = min(frame.shape[0], y + new_h)

        # Calculate template region
        tx1 = x1 - x
        ty1 = y1 - y
        tx2 = tx1 + (x2 - x1)
        ty2 = ty1 + (y2 - y1)

        if tx2 > tx1 and ty2 > ty1 and x2 > x1 and y2 > y1:
            template_region = resized_template[ty1:ty2, tx1:tx2]

            if alpha is not None:
                # Resize alpha channel (2D array: height, width)
                resized_alpha = cv2.resize(alpha, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                alpha_region = resized_alpha[ty1:ty2, tx1:tx2]

                # Blend with alpha (optimized)
                # Alpha is 2D (height, width), need to expand to 3D (height, width, 3) for BGR
                alpha_3d = np.expand_dims(alpha_region, axis=2)  # (H, W, 1)
                alpha_3d = np.repeat(alpha_3d, 3, axis=2)  # (H, W, 3)

                # Normalize to 0-1 range and blend (vectorized)
                alpha_norm = alpha_3d.astype(np.float32) * (1.0 / 255.0)
                frame_region = frame[y1:y2, x1:x2].astype(np.float32)
                template_float = template_region.astype(np.float32)
                # In-place operations where possible
                blended = frame_region * (1.0 - alpha_norm) + template_float * alpha_norm
                frame[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
            else:
                # Simple paste (no transparency) - fastest path
                frame[y1:y2, x1:x2] = template_region

    def _draw_synthetic_droplet(
        self,
        frame: np.ndarray,
        pos: List[float],
        radius: float,
        aspect_ratio: float,
        intensity: float,
    ) -> None:
        """Draw a synthetic droplet with reduced contrast (optimized)."""
        center = (int(pos[0]), int(pos[1]))

        # Calculate ellipse axes based on aspect ratio
        if aspect_ratio >= 1.0:
            axes = (int(radius * aspect_ratio), int(radius))
            angle = 0
        else:
            axes = (int(radius), int(radius / aspect_ratio))
            angle = 90

        # Calculate color based on intensity (less contrast)
        # Base color: gray-white, not pure white
        base_color = int(180 + 75 * intensity)  # Range: 180-255 (not pure white)
        color = (base_color, base_color, base_color)

        # Draw filled ellipse (simplified - no highlight for performance)
        cv2.ellipse(frame, center, axes, angle, 0, 360, color, -1)

    def start(self):
        """Start camera capture thread."""
        if self.cam_running_event and self.cam_running_event.is_set():
            return  # Already running

        if self.cam_running_event:
            self.cam_running_event.set()
        self.frame_thread = Thread(
            target=self._capture_loop, daemon=True, name="SimulatedCameraThread"
        )
        self.frame_thread.start()
        self.running = True
        logger.info(f"SimulatedCamera started ({self.width}x{self.height} @ {self.fps} FPS)")

    def stop(self):
        """
        Stop camera capture.

        Clears the running event and waits for the frame thread to terminate.
        """
        if not self.cam_running_event or not self.cam_running_event.is_set():
            return  # Already stopped

        if self.cam_running_event:
            self.cam_running_event.clear()
        if self.frame_thread:
            self.frame_thread.join(timeout=2.0)
            if self.frame_thread.is_alive():
                logger.warning("SimulatedCamera thread did not terminate within timeout")
        self.running = False
        logger.debug("SimulatedCamera stopped")

    def _capture_loop(self):
        """Main capture loop (runs in background thread)."""
        frame_time = 1.0 / max(1, self.fps)

        while self.cam_running_event and self.cam_running_event.is_set():
            start_time = time.time()

            # Generate frame
            self.current_frame = self._generate_frame()

            # Call frame callback (for strobe trigger)
            if self.frame_callback:
                try:
                    self.frame_callback()
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")

            # Maintain frame rate with a small minimum sleep to avoid tight loops
            elapsed = time.time() - start_time
            sleep_time = max(0.005, frame_time - elapsed)
            time.sleep(sleep_time)

    def get_frame_array(self) -> Optional[np.ndarray]:
        """
        Get current frame as numpy array.

        Returns:
            BGR numpy array or None if not available
        """
        return self.current_frame

    def get_frame_roi(self, roi_coords: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Get ROI frame.

        Args:
            roi_coords: (x, y, width, height) tuple

        Returns:
            Cropped frame or None
        """
        if self.current_frame is None:
            return None

        x, y, w, h = roi_coords
        # Clamp to frame bounds
        x = max(0, min(x, self.width))
        y = max(0, min(y, self.height))
        w = min(w, self.width - x)
        h = min(h, self.height - y)

        return self.current_frame[y : y + h, x : x + w]

    def set_config(self, config: dict) -> None:
        """Update camera configuration."""
        if "Width" in config:
            self.width = int(config["Width"])
            size_list = self.config.get("size", [640, 480])
            if isinstance(size_list, list):
                size_list[0] = self.width
                self.config["size"] = size_list
        if "Height" in config:
            self.height = int(config["Height"])
            size_list = self.config.get("size", [640, 480])
            if isinstance(size_list, list):
                size_list[1] = self.height
                self.config["size"] = size_list
        if "FrameRate" in config:
            self.fps = int(config["FrameRate"])
            self.config["FrameRate"] = self.fps
        if "ShutterSpeed" in config:
            self.config["ShutterSpeed"] = int(config["ShutterSpeed"])

        # Reinitialize droplets if size changed
        if "Width" in config or "Height" in config:
            # Reload background if dimensions changed
            if self.background_image is not None:
                self._load_real_images()
            # Clear existing droplets
            self.droplet_positions = []
            self.droplet_velocities = []
            self.droplet_sizes = []
            self.droplet_aspect_ratios = []
            self.droplet_templates_idx = []
            self.droplet_intensities = []
            self._initialize_droplets()

        # Restart if running
        was_running = self.cam_running_event and self.cam_running_event.is_set()
        if was_running:
            self.stop()
            self.start()

    def set_roi_hardware(self, roi: tuple[int, int, int, int]) -> bool:
        """
        Simulation does not support hardware ROI; always return False so callers
        can fall back to software ROI without repeated warnings.
        """
        return False

    def set_frame_callback(self, callback: Optional[Callable[[], None]]):
        """Set frame callback (called on each frame capture)."""
        self.frame_callback = callback

    def close(self):
        """Close camera (alias for stop for compatibility)."""
        self.stop()

    def generate_frames(self, config=None):
        """
        Generator that yields JPEG-encoded frames (for web streaming).

        This method is compatible with the old camera interface.
        """
        if config:
            self.set_config(config)

        if not self.cam_running_event or not self.cam_running_event.is_set():
            self.start()

        # Wait a bit for first frame
        time.sleep(FRAME_WAIT_TIME_S)

        while self.cam_running_event and self.cam_running_event.is_set():
            frame = self.get_frame_array()
            if frame is not None:
                # Encode as JPEG
                try:
                    _, buffer = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                    )
                    if buffer is not None:
                        yield buffer.tobytes()
                except Exception as e:
                    logger.error(f"Error encoding frame as JPEG: {e}")
            time.sleep(1.0 / self.fps)
