"""
Camera controller for handling camera and strobe WebSocket events.

This module handles all camera-related WebSocket commands, keeping the
controller logic separate from the view and model layers.

Classes:
    CameraController: Handles camera and strobe WebSocket events
"""

import logging
import sys
import os
from typing import Dict, Any
from flask_socketio import SocketIO

# Add parent directories to path for imports (software/ level)
software_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if software_root not in sys.path:
    sys.path.insert(0, software_root)
from controllers.camera import Camera  # noqa: E402

# Configure logging
logger = logging.getLogger(__name__)


class CameraController:
    """
    Controller for camera and strobe operations.

    Handles WebSocket events related to camera selection, strobe control,
    and ROI management. Keeps controller logic separate from view and model.
    """

    def __init__(self, camera: Camera, socketio: SocketIO):
        """
        Initialize camera controller.

        Args:
            camera: Camera model instance
            socketio: Flask-SocketIO instance for WebSocket communication
        """
        self.camera = camera
        self.socketio = socketio
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register WebSocket event handlers."""
        logger.debug("CameraController registering WebSocket handler: cam_select")

        @self.socketio.on("cam_select")
        def on_cam_select(data: Dict[str, Any]) -> None:
            self.handle_camera_select(data)

        logger.debug("CameraController WebSocket handler registered successfully")

    def _stop_camera_thread(self) -> None:
        """Stop the current camera thread if it's running."""
        if not (
            hasattr(self.camera, "thread") and self.camera.thread and self.camera.thread.is_alive()
        ):
            return

        if hasattr(self.camera, "exit_event"):
            self.camera.exit_event.set()
        try:
            self.camera.thread.join(timeout=2.0)
        except Exception:
            pass

    def _set_camera_type(self, camera_name: str) -> str:
        """
        Set camera type in strobe_cam and handle errors.

        Args:
            camera_name: Name of camera to set

        Returns:
            Actual camera name (may be 'none' if setting failed)
        """
        if not hasattr(self.camera, "strobe_cam"):
            return camera_name

        success = self.camera.strobe_cam.set_camera_type(camera_name)
        if not success and camera_name != "none":
            logger.error(f"Failed to set camera type to {camera_name}")
            return "none"  # Fall back to none on error

        return camera_name

    def _update_camera_instance(self, camera_name: str) -> None:
        """
        Update camera instance based on camera name.

        Args:
            camera_name: Name of camera ('none' or camera type)
        """
        self.camera.cam_data["camera"] = camera_name
        if camera_name != "none" and self.camera.strobe_cam and self.camera.strobe_cam.camera:
            self.camera.camera = self.camera.strobe_cam.camera
        else:
            self.camera.camera = None

    def handle_camera_select(self, data: Dict[str, Any]) -> None:
        """
        Handle camera selection command.

        Args:
            data: Dictionary containing 'cmd' and 'parameters' keys
        """
        try:
            if data.get("cmd") != "select":
                logger.warning(f"Unknown camera command: {data.get('cmd')}")
                return

            camera_name = data.get("parameters", {}).get("camera", "none")
            logger.info(f"Camera selection changed to: {camera_name}")

            # Stop current camera thread if running
            self._stop_camera_thread()

            # Set camera type in strobe_cam (will create appropriate camera instance)
            camera_name = self._set_camera_type(camera_name)

            # Update camera data and instance
            self._update_camera_instance(camera_name)

            # Emit reload to trigger page refresh
            self.socketio.emit("reload")
        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"Error handling camera select: {e}")
            logger.debug(f"Command data: {data}")
