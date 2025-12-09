"""
Camera Abstraction Layer
Unified interface for 32-bit and 64-bit Raspberry Pi cameras

Based on tested code from flow-microscopy-platform repository:
- PiCamera32 (32-bit, picamera library)
- PiCamera (64-bit, picamera2 library)
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple, Dict, Generator
import numpy as np
import platform
import os


class BaseCamera(ABC):
    """
    Unified camera interface for 32-bit and 64-bit Raspberry Pi
    
    This abstract base class provides a common interface for both
    picamera (32-bit) and picamera2 (64-bit) implementations.
    Based on tested code from flow-microscopy-platform repository.
    """
    
    def __init__(self):
        self.config = {
            "size": [640, 480],
            "FrameRate": 30,
            "ShutterSpeed": 10000
        }
        self.frame_callback: Optional[Callable[[], None]] = None
        self.cam_running_event = None  # Set by subclasses
        self.capture_flag = None  # Set by subclasses
        self.capture_queue = None  # Set by subclasses
    
    @abstractmethod
    def start(self) -> None:
        """Start camera capture"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop camera capture"""
        pass
    
    @abstractmethod
    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        """
        Generate frames (generator) - for streaming
        
        Yields:
            bytes: JPEG-encoded frame data
        """
        pass
    
    @abstractmethod
    def get_frame_array(self) -> np.ndarray:
        """
        Get single frame as numpy array
        
        Returns:
            numpy.ndarray: Frame as numpy array (RGB format)
        """
        pass
    
    @abstractmethod
    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI (Region of Interest) frame as numpy array
        
        Args:
            roi: (x, y, width, height) tuple defining ROI
        
        Returns:
            numpy.ndarray: ROI frame as numpy array (RGB format)
        """
        pass
    
    def set_frame_callback(self, callback: Optional[Callable[[], None]]):
        """
        Set callback function called on each frame capture
        
        Args:
            callback: Function to call on each frame (no arguments)
        """
        self.frame_callback = callback
    
    def set_config(self, configs: Dict):
        """
        Update camera configuration
        
        Args:
            configs: Dictionary of configuration parameters
                   (Height, Width, FrameRate, ShutterSpeed, etc.)
        """
        # Base implementation - subclasses should override
        self.config.update(configs)
    
    def capture_image(self):
        """Request a single frame capture"""
        if self.capture_flag:
            self.capture_flag.set()
    
    def get_capture(self) -> np.ndarray:
        """
        Get captured frame (after calling capture_image())
        
        Returns:
            numpy.ndarray: Captured frame
        """
        if self.capture_queue:
            return self.capture_queue.get()
        raise RuntimeError("Capture queue not initialized")
    
    def close(self):
        """Cleanup and close camera"""
        self.stop()
    
    def list_features(self) -> list:
        """
        List available camera features for UI
        
        Returns:
            list: List of feature dictionaries
        """
        return []


def create_camera(simulation: bool = False, sim_config: dict = None) -> BaseCamera:
    """
    Factory function to create appropriate camera instance
    
    Auto-detects OS architecture and available libraries:
    - Simulation mode → SimulatedCamera
    - 64-bit OS + picamera2 available → PiCameraV2
    - 32-bit OS or picamera2 unavailable → PiCameraLegacy
    
    Args:
        simulation: If True, return simulated camera
        sim_config: Optional simulation configuration dict
    
    Returns:
        BaseCamera: Appropriate camera instance
    
    Raises:
        RuntimeError: If no camera library is available (and not in simulation mode)
    """
    # Check for simulation mode first
    if simulation:
        try:
            from ..simulation.camera_simulated import SimulatedCamera
            if sim_config:
                return SimulatedCamera(**sim_config)
            return SimulatedCamera()
        except ImportError:
            print("Warning: Simulation module not available, falling back to real camera")
    
    # Check environment variable for simulation
    import os
    if os.getenv('RIO_SIMULATION', 'false').lower() == 'true':
        try:
            from ..simulation.camera_simulated import SimulatedCamera
            return SimulatedCamera()
        except ImportError:
            print("Warning: Simulation module not available, falling back to real camera")
    
    # Check if 64-bit OS
    machine = platform.machine()
    is_64bit = machine == 'aarch64' or machine == 'arm64'
    
    # Try 64-bit first (picamera2)
    if is_64bit:
        try:
            from picamera2 import Picamera2
            # Test if we can actually create a camera
            test_cam = Picamera2()
            test_cam.close()
            del test_cam
            
            from .pi_camera_v2 import PiCameraV2
            return PiCameraV2()
        except (ImportError, Exception) as e:
            # Fall back to 32-bit if picamera2 not available
            print(f"picamera2 not available ({e}), falling back to picamera")
    
    # Fall back to 32-bit (picamera)
    try:
        from picamera import PiCamera
        from .pi_camera_legacy import PiCameraLegacy
        return PiCameraLegacy()
    except ImportError:
        raise RuntimeError(
            "No camera library available. "
            "Install either 'picamera' (32-bit) or 'picamera2' (64-bit), "
            "or enable simulation mode (RIO_SIMULATION=true)"
        )

