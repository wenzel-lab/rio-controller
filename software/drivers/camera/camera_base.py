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
import logging

logger = logging.getLogger(__name__)

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

        np = type("np", (), {"ndarray": _DummyNDArray})()


class BaseCamera(ABC):
    """
    Unified camera interface for 32-bit and 64-bit Raspberry Pi

    This abstract base class provides a common interface for both
    picamera (32-bit) and picamera2 (64-bit) implementations.
    Based on tested code from flow-microscopy-platform repository.
    """

    def __init__(self):
        self.config = {"size": [640, 480], "FrameRate": 30, "ShutterSpeed": 10000}
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
    def get_frame_roi(
        self, roi: Tuple[int, int, int, int]
    ) -> Any:  # np.ndarray when numpy available
        """
        Get ROI (Region of Interest) frame as numpy array

        Args:
            roi: (x, y, width, height) tuple defining ROI

        Returns:
            numpy.ndarray: ROI frame as numpy array (RGB format)
        """
        pass

    def capture_frame_at_resolution(self, width: int, height: int) -> bytes:
        """
        Capture a single frame at specified resolution (for snapshots).

        This temporarily changes the camera resolution, captures a frame,
        and restores the original resolution. Useful for full-resolution snapshots.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels

        Returns:
            bytes: JPEG-encoded frame data
        """
        # Default implementation: subclasses should override if they can do this efficiently
        # For now, fall back to get_frame_array and encode as JPEG
        import io
        from PIL import Image

        frame_array = self.get_frame_array()
        img = Image.fromarray(frame_array)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()

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

    def get_actual_framerate(self) -> float:
        """
        Get actual framerate from camera hardware.

        Returns the actual framerate that the camera is using, which may differ
        from the configured value due to hardware limitations or rounding.

        This is a default implementation that returns the config value.
        Subclasses should override to read from actual hardware.

        Returns:
            float: Actual framerate in FPS
        """
        return float(self.config.get("FrameRate", 30))

    def get_actual_shutter_speed(self) -> int:
        """
        Get actual shutter speed from camera hardware.

        Returns the actual shutter speed that the camera is using (in microseconds),
        which may differ from the configured value due to hardware limitations.

        This is a default implementation that returns the config value.
        Subclasses should override to read from actual hardware.

        Returns:
            int: Actual shutter speed in microseconds
        """
        return int(self.config.get("ShutterSpeed", 10000))

    def list_features(self) -> list:
        """
        List available camera features for UI

        Returns:
            list: List of feature dictionaries
        """
        return []


def create_camera(
    camera_type: Optional[str] = None,
    simulation: bool = False,
    sim_config: Optional[Dict[str, Any]] = None,
) -> BaseCamera:
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

    # Check for simulation mode first
    if simulation or os.getenv("RIO_SIMULATION", "false").lower() == "true":
        return _create_simulated_camera(simulation, sim_config)

    # Check for specific camera type
    if camera_type == "mako":
        return _create_mako_camera()
    if camera_type == "rpi_hq":
        camera_type = "rpi"  # Fall through to rpi handling

    # Auto-detect based on platform
    return _create_pi_camera()


def _create_simulated_camera(
    simulation: bool, sim_config: Optional[Dict[str, Any]] = None
) -> BaseCamera:
    """Create simulated camera instance."""
    import sys
    import os as os_module

    current_file = os_module.path.abspath(__file__)
    parent_dir = os_module.path.dirname(os_module.path.dirname(current_file))

    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        from simulation.camera_simulated import SimulatedCamera

        if sim_config:
            return SimulatedCamera(**sim_config)
        return SimulatedCamera()
    except ImportError as e1:
        try:
            sim_path = os_module.path.join(parent_dir, "simulation")
            if sim_path not in sys.path:
                sys.path.insert(0, sim_path)
            from camera_simulated import SimulatedCamera  # type: ignore[no-redef]

            return SimulatedCamera()
        except ImportError as e2:
            error_msg = (
                str(e1) if "numpy" in str(e1).lower() or "cv2" in str(e1).lower() else str(e2)
            )
            if "numpy" in error_msg.lower() or "cv2" in error_msg.lower():
                raise ImportError(
                    f"Simulation dependencies missing: {error_msg}. "
                    "Install with: pip install numpy opencv-python"
                )
            raise ImportError(f"Could not import SimulatedCamera: {error_msg}")


def _create_mako_camera() -> BaseCamera:
    """Create MAKO camera instance."""
    try:
        from .mako_camera import MakoCamera

        return MakoCamera()
    except ImportError:
        raise RuntimeError(
            "MAKO camera requested but vimba-python not available. "
            "Install with: pip install vimba-python"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize MAKO camera: {e}")


def _create_pi_camera() -> BaseCamera:
    """Create Raspberry Pi camera instance (auto-detect 32/64-bit)."""
    # Check strobe control mode: strobe-centric mode REQUIRES picamera (32-bit legacy)
    # Don't try picamera2 first if we're in strobe-centric mode
    import os
    strobe_mode = os.getenv("RIO_STROBE_CONTROL_MODE", "").lower()
    if strobe_mode in ("strobe-centric", "legacy"):
        # Strobe-centric mode requires picamera (legacy), skip picamera2 entirely
        logger.info("Strobe-centric mode detected: using picamera (legacy) only, skipping picamera2")
        try:
            import picamera  # noqa: F401
            from .pi_camera_legacy import PiCameraLegacy
            return PiCameraLegacy()
        except ImportError:
            raise RuntimeError(
                "Strobe-centric mode requires picamera library (32-bit). "
                "Install with: sudo apt-get install python3-picamera"
            )
    
    # For camera-centric or auto-detect, check architecture
    machine = platform.machine()
    is_64bit = machine == "aarch64" or machine == "arm64"

    if is_64bit:
        try:
            from picamera2 import Picamera2

            test_cam = Picamera2()
            test_cam.close()
            del test_cam

            from .pi_camera_v2 import PiCameraV2

            return PiCameraV2()
        except (ImportError, Exception) as e:
            print(f"picamera2 not available ({e}), falling back to picamera")

    try:
        import picamera  # noqa: F401

        from .pi_camera_legacy import PiCameraLegacy

        return PiCameraLegacy()
    except ImportError:
        if machine not in ("armv7l", "aarch64", "arm64"):
            raise RuntimeError(
                "No camera library available on this platform. "
                "Enable simulation mode: export RIO_SIMULATION=true"
            )
        raise RuntimeError(
            "No camera library available. "
            "Install either 'picamera' (32-bit) or 'picamera2' (64-bit), "
            "or enable simulation mode (RIO_SIMULATION=true)"
        )
