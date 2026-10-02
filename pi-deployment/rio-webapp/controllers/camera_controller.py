"""
Camera controller for handling camera and strobe WebSocket events.

This module handles all camera-related WebSocket commands, keeping the
controller logic separate from the view and model layers.

Classes:
    CameraController: Handles camera and strobe WebSocket events
"""

import logging
from typing import Dict, Any
from flask_socketio import SocketIO

from controllers.camera import Camera

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
        """Stop the capture thread when switching camera (same pattern as Camera._restart_camera_thread)."""
        cam = self.camera
        if not (hasattr(cam, "thread") and cam.thread and cam.thread.is_alive()):
            return

        logger.debug("Stopping camera thread for camera switch")
        if hasattr(cam, "exit_event"):
            cam.exit_event.set()
        thread = getattr(cam, "thread", None)
        if thread is not None:
            try:
                thread.join(timeout=3.0)
                if thread.is_alive():
                    logger.warning("Camera thread did not stop within timeout during switch")
            except Exception as e:
                logger.warning("Error waiting for camera thread during switch: %s", e)
        cam.thread = None
        cam.frame = None
        # Must clear: exit_event is app-wide; leaving it set blocks initialize() -> white video
        if hasattr(cam, "exit_event"):
            cam.exit_event.clear()

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
            self.camera.bind_camera_backend(self.camera.strobe_cam.camera)
            if hasattr(self.camera, "_sync_default_stream_resolution"):
                self.camera._sync_default_stream_resolution()
        else:
            self.camera.bind_camera_backend(None)

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

            # Re-selecting the same live camera must be a no-op. Stopping the
            # capture thread + emitting "reload" races the Galaxy handle and
            # leaves Enable on free-run with a dead LineOut (_device is None).
            current = (self.camera.cam_data or {}).get("camera")
            live_backend = (
                getattr(self.camera, "strobe_cam", None)
                and self.camera.strobe_cam.camera is not None
                and self.camera.camera is self.camera.strobe_cam.camera
            )
            if camera_name == current and live_backend and camera_name != "none":
                if self.camera.thread is None or not self.camera.thread.is_alive():
                    try:
                        self.camera.initialize()
                    except Exception as e:
                        logger.error("Failed to restart camera thread: %s", e)
                logger.info("Camera already %s — skip switch/reload", camera_name)
                return

            # Stop current camera thread if running
            self._stop_camera_thread()

            # Set camera type in strobe_cam (will create appropriate camera instance)
            camera_name = self._set_camera_type(camera_name)

            # Update camera data and instance
            self._update_camera_instance(camera_name)

            # Start capture before reload so /video has frames (Daheng/Mako)
            if camera_name != "none":
                try:
                    self.camera.initialize()
                except Exception as e:
                    logger.error("Failed to start camera after switch: %s", e)

            # Emit reload to refresh UI (selection, ROI widgets)
            self.socketio.emit("reload")
        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"Error handling camera select: {e}")
            logger.debug(f"Command data: {data}")
