"""
Camera Abstraction Layer
Unified interface for 32-bit and 64-bit Raspberry Pi cameras

Based on tested code from flow-microscopy-platform repository:
- PiCamera32 (32-bit, picamera library)
- PiCamera (64-bit, picamera2 library)
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple, Dict, Generator, TYPE_CHECKING, Any
import platform
import os

# numpy is only needed for type hints and actual camera implementations
# Make it optional so the base class can be imported without numpy
if TYPE_CHECKING:
    import numpy as np
else:
    try:
        import numpy as np
    except ImportError:
        # Create a dummy class for type hints when numpy isn't available
        class _DummyNDArray:
            pass
        np = type('np', (), {'ndarray': _DummyNDArray})()


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
    def get_frame_array(self) -> Any:  # np.ndarray when numpy available
        """
        Get single frame as numpy array
        
        Returns:
            numpy.ndarray: Frame as numpy array (RGB format)
        """
        pass
    
    @abstractmethod
    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> Any:  # np.ndarray when numpy available
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


def create_camera(camera_type: str = None, simulation: bool = False, sim_config: dict = None) -> BaseCamera:
    """
    Factory function to create appropriate camera instance
    
    Camera types:
    - 'mako' → MakoCamera (requires vimba-python)
    - 'rpi_hq' → PiCameraV2 (HQ Camera, requires picamera2 on 64-bit)
    - 'rpi' → PiCameraV2 (V2 Camera, requires picamera2 on 64-bit) or PiCameraLegacy (32-bit)
    - None → Auto-detect based on available hardware
    
    Auto-detection:
    - Simulation mode → SimulatedCamera
    - 64-bit OS + picamera2 available → PiCameraV2
    - 32-bit OS or picamera2 unavailable → PiCameraLegacy
    
    Args:
        camera_type: Camera type ('mako', 'rpi_hq', 'rpi', or None for auto-detect)
        simulation: If True, return simulated camera
        sim_config: Optional simulation configuration dict
    
    Returns:
        BaseCamera: Appropriate camera instance
    
    Raises:
        RuntimeError: If no camera library is available (and not in simulation mode)
    """
    import os
    
    # Helper function to import simulation camera
    def _import_simulated_camera():
        """Import SimulatedCamera with multiple fallback strategies."""
        import sys
        import os as os_module
        
        # Get the parent directory (src/)
        current_file = os_module.path.abspath(__file__)
        parent_dir = os_module.path.dirname(os_module.path.dirname(current_file))
        
        # Strategy 1: Add parent directory to path and import
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        try:
            from simulation.camera_simulated import SimulatedCamera
            return SimulatedCamera
        except ImportError as e1:
            # Strategy 2: Try importing from absolute path
            try:
                sim_path = os_module.path.join(parent_dir, 'simulation')
                if sim_path not in sys.path:
                    sys.path.insert(0, sim_path)
                from camera_simulated import SimulatedCamera
                return SimulatedCamera
            except ImportError as e2:
                # Check if it's a missing dependency (numpy/opencv) vs path issue
                error_msg = str(e1) if 'numpy' in str(e1).lower() or 'cv2' in str(e1).lower() else str(e2)
                if 'numpy' in error_msg.lower() or 'cv2' in error_msg.lower() or 'opencv' in error_msg.lower():
                    raise ImportError(f"Simulation dependencies missing: {error_msg}. Install with: pip install numpy opencv-python")
                raise ImportError(f"Could not import SimulatedCamera: {error_msg}")
    
    # Check for simulation mode first (explicit parameter)
    if simulation:
        try:
            SimulatedCamera = _import_simulated_camera()
            if sim_config:
                return SimulatedCamera(**sim_config)
            return SimulatedCamera()
        except ImportError as e:
            print(f"Warning: Simulation module not available ({e}), falling back to real camera")
    
    # Check environment variable for simulation
    if os.getenv('RIO_SIMULATION', 'false').lower() == 'true':
        try:
            SimulatedCamera = _import_simulated_camera()
            return SimulatedCamera()
        except ImportError as e:
            print(f"Warning: Simulation module not available ({e})")
            # In simulation mode, we should use simulated camera, so raise error
            raise RuntimeError(
                "Simulation mode enabled but simulation module unavailable. "
                "Install dependencies: pip install numpy opencv-python"
            )
    
    # Check for specific camera type
    if camera_type == 'mako':
        try:
            from .mako_camera import MakoCamera
            return MakoCamera()
        except ImportError as e:
            raise RuntimeError(
                "MAKO camera requested but vimba-python not available. "
                "Install with: pip install vimba-python"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MAKO camera: {e}")
    
    if camera_type == 'rpi_hq':
        # HQ Camera uses same implementation as V2 (picamera2 auto-detects)
        camera_type = 'rpi'  # Fall through to rpi handling
    
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
            
            # Import only when we know picamera2 is available
            from .pi_camera_v2 import PiCameraV2
            return PiCameraV2()
        except (ImportError, Exception) as e:
            # Fall back to 32-bit if picamera2 not available
            print(f"picamera2 not available ({e}), falling back to picamera")
    
    # Fall back to 32-bit (picamera)
    try:
        from picamera import PiCamera
        # Import only when we know picamera is available
        from .pi_camera_legacy import PiCameraLegacy
        return PiCameraLegacy()
    except ImportError:
        # If we're not on a Raspberry Pi, suggest simulation mode
        if machine not in ('armv7l', 'aarch64', 'arm64'):
            raise RuntimeError(
                "No camera library available on this platform. "
                "Enable simulation mode: export RIO_SIMULATION=true"
            )
        raise RuntimeError(
            "No camera library available. "
            "Install either 'picamera' (32-bit) or 'picamera2' (64-bit), "
            "or enable simulation mode (RIO_SIMULATION=true)"
        )

