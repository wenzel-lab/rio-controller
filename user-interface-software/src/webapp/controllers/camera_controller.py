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
from typing import Dict, Any, Optional
from flask_socketio import SocketIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from camera_pi import Camera

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
        @self.socketio.on('cam_select')
        def on_cam_select(data: Dict[str, Any]) -> None:
            self.handle_camera_select(data)
    
    def handle_camera_select(self, data: Dict[str, Any]) -> None:
        """
        Handle camera selection command.
        
        Args:
            data: Dictionary containing 'cmd' and 'parameters' keys
        """
        try:
            if data.get('cmd') != 'select':
                logger.warning(f"Unknown camera command: {data.get('cmd')}")
                return
            
            camera_name = data.get('parameters', {}).get('camera', 'none')
            self.camera.cam_data['camera'] = camera_name
            logger.info(f"Camera selection changed to: {camera_name}")
            
            # If switching to 'none', stop the camera immediately
            if camera_name == 'none':
                logger.info("Stopping camera stream...")
                try:
                    if hasattr(self.camera, 'camera') and self.camera.camera:
                        self.camera.camera.stop()
                    if hasattr(self.camera, 'thread') and self.camera.thread and self.camera.thread.is_alive():
                        if hasattr(self.camera, 'exit_event'):
                            self.camera.exit_event.set()
                except Exception as e:
                    logger.error(f"Error stopping camera: {e}")
            else:
                logger.info(f"Camera set to: {camera_name}")
            
            # Emit reload to trigger page refresh
            self.socketio.emit('reload')
        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"Error handling camera select: {e}")
            logger.debug(f"Command data: {data}")

