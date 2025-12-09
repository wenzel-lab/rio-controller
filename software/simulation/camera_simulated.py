"""
Simulated camera implementation.

Generates synthetic frames with optional droplet patterns for testing without
physical hardware. This module provides a drop-in replacement for real camera
implementations, allowing the application to run and be tested on any system.

Classes:
    SimulatedCamera: Camera implementation that generates synthetic frames
"""

import numpy as np
import cv2
import time
import logging
from typing import Optional, Callable, Tuple
from threading import Event, Thread

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 30
DEFAULT_DROPLET_COUNT = 5
DEFAULT_DROPLET_SIZE_RANGE = (10, 50)
JPEG_QUALITY = 85
FRAME_WAIT_TIME_S = 0.1

# Try to import real camera classes (will fail on non-Pi systems, that's OK)
try:
    from ..droplet_detection.camera_base import BaseCamera
except ImportError:
    # Fallback for when droplet_detection not available
    from abc import ABC, abstractmethod
    class BaseCamera(ABC):
        @abstractmethod
        def start(self): pass
        @abstractmethod
        def stop(self): pass
        @abstractmethod
        def get_frame_array(self): pass
        @abstractmethod
        def get_frame_roi(self, roi_coords): pass
        @abstractmethod
        def set_config(self, config): pass
        @abstractmethod
        def set_frame_callback(self, callback): pass


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
    
    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 fps: int = DEFAULT_FPS, generate_droplets: bool = True,
                 droplet_count: int = DEFAULT_DROPLET_COUNT,
                 droplet_size_range: Tuple[int, int] = DEFAULT_DROPLET_SIZE_RANGE):
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
        
        logger.debug(f"Initializing SimulatedCamera: {width}x{height} @ {fps}fps, droplets={generate_droplets}")
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
        
        self.cam_running_event = Event()
        self.frame_callback: Optional[Callable[[], None]] = None
        self.current_frame: Optional[np.ndarray] = None
        self.frame_thread: Optional[Thread] = None
        
        # For droplet animation
        self.frame_counter = 0
        self.droplet_positions = []
        self.droplet_velocities = []
        self._initialize_droplets()
    
    def _initialize_droplets(self):
        """Initialize random droplet positions and velocities."""
        self.droplet_positions = []
        self.droplet_velocities = []
        
        for _ in range(self.droplet_count):
            # Random starting position
            x = np.random.randint(50, self.width - 50)
            y = np.random.randint(50, self.height - 50)
            self.droplet_positions.append([x, y])
            
            # Random velocity (pixels per frame)
            vx = np.random.uniform(-2, 2)
            vy = np.random.uniform(-2, 2)
            self.droplet_velocities.append([vx, vy])
    
    def _generate_frame(self) -> np.ndarray:
        """
        Generate a synthetic frame.
        
        Returns:
            numpy array (BGR format for OpenCV compatibility)
        """
        # Create base frame (dark background, typical for microfluidics)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (20, 20, 20)  # Dark gray background
        
        if self.generate_droplets:
            # Update droplet positions
            for i, (pos, vel) in enumerate(zip(self.droplet_positions, self.droplet_velocities)):
                # Update position
                pos[0] += vel[0]
                pos[1] += vel[1]
                
                # Bounce off edges
                if pos[0] < 30 or pos[0] > self.width - 30:
                    vel[0] *= -1
                if pos[1] < 30 or pos[1] > self.height - 30:
                    vel[1] *= -1
                
                # Clamp position
                pos[0] = np.clip(pos[0], 30, self.width - 30)
                pos[1] = np.clip(pos[1], 30, self.height - 30)
                
                # Draw droplet (bright circle)
                radius = np.random.randint(self.droplet_size_range[0], self.droplet_size_range[1])
                cv2.circle(frame, (int(pos[0]), int(pos[1])), radius, (255, 255, 255), -1)
                # Add highlight
                cv2.circle(frame, (int(pos[0] - radius//3), int(pos[1] - radius//3)), 
                          radius//3, (200, 200, 200), -1)
        
        # Add some noise (simulate sensor noise)
        noise = np.random.randint(-5, 5, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        self.frame_counter += 1
        return frame
    
    def start(self):
        """Start camera capture thread."""
        if self.cam_running_event.is_set():
            return  # Already running
        
        self.cam_running_event.set()
        self.frame_thread = Thread(target=self._capture_loop, daemon=True, name="SimulatedCameraThread")
        self.frame_thread.start()
        logger.info(f"SimulatedCamera started ({self.width}x{self.height} @ {self.fps} FPS)")
    
    def stop(self):
        """
        Stop camera capture.
        
        Clears the running event and waits for the frame thread to terminate.
        """
        if not self.cam_running_event.is_set():
            return  # Already stopped
        
        self.cam_running_event.clear()
        if self.frame_thread:
            self.frame_thread.join(timeout=2.0)
            if self.frame_thread.is_alive():
                logger.warning("SimulatedCamera thread did not terminate within timeout")
        logger.debug("SimulatedCamera stopped")
    
    def _capture_loop(self):
        """Main capture loop (runs in background thread)."""
        frame_time = 1.0 / self.fps
        
        while self.cam_running_event.is_set():
            start_time = time.time()
            
            # Generate frame
            self.current_frame = self._generate_frame()
            
            # Call frame callback (for strobe trigger)
            if self.frame_callback:
                try:
                    self.frame_callback()
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")
            
            # Maintain frame rate
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
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
        
        return self.current_frame[y:y+h, x:x+w]
    
    def set_config(self, config: dict):
        """Update camera configuration."""
        if "Width" in config:
            self.width = int(config["Width"])
            self.config["size"][0] = self.width
        if "Height" in config:
            self.height = int(config["Height"])
            self.config["size"][1] = self.height
        if "FrameRate" in config:
            self.fps = int(config["FrameRate"])
            self.config["FrameRate"] = self.fps
        if "ShutterSpeed" in config:
            self.config["ShutterSpeed"] = int(config["ShutterSpeed"])
        
        # Reinitialize droplets if size changed
        if "Width" in config or "Height" in config:
            self._initialize_droplets()
        
        # Restart if running
        was_running = self.cam_running_event.is_set()
        if was_running:
            self.stop()
            self.start()
    
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
        
        if not self.cam_running_event.is_set():
            self.start()
        
        # Wait a bit for first frame
        time.sleep(FRAME_WAIT_TIME_S)
        
        while self.cam_running_event.is_set():
            frame = self.get_frame_array()
            if frame is not None:
                # Encode as JPEG
                try:
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                    if buffer is not None:
                        yield buffer.tobytes()
                except Exception as e:
                    logger.error(f"Error encoding frame as JPEG: {e}")
            time.sleep(1.0 / self.fps)

