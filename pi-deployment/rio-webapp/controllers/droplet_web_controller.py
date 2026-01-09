"""
Droplet detection web controller for handling droplet detection WebSocket events.

This module handles all droplet detection-related WebSocket commands, keeping the
controller logic separate from the view and model layers.

Classes:
    DropletWebController: Handles droplet detection WebSocket events
"""

import logging
import time
from typing import Dict, Any, Callable
from flask_socketio import SocketIO

from controllers.droplet_detector_controller import DropletDetectorController

# Configure logging
logger = logging.getLogger(__name__)


class DropletWebController:
    """
    Controller for droplet detection operations.

    Handles WebSocket events related to droplet detection control,
    configuration, and real-time updates. Keeps controller logic separate
    from view and model layers.
    """

    def __init__(self, droplet_controller: DropletDetectorController, socketio: SocketIO):
        """
        Initialize droplet web controller.

        Args:
            droplet_controller: DropletDetectorController instance
            socketio: Flask-SocketIO instance for WebSocket communication
        """
        self.droplet_controller = droplet_controller
        self.socketio = socketio
        self.last_emit_time: Dict[str, float] = {}  # Track last emit time for rate limiting
        self.emit_intervals = {
            "histogram": 2.0,  # 0.5 Hz (once every 2 seconds)
            "statistics": 2.0,  # 0.5 Hz (once every 2 seconds)
            "performance": 1.0,  # 1 Hz (debug only)
        }
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register WebSocket event handlers."""

        @self.socketio.on("droplet")
        def on_droplet(data: Dict[str, Any]) -> None:
            """Handle droplet detection commands."""
            self.handle_droplet_command(data)

    def _handle_start_command(self) -> None:
        """Handle start command."""
        try:
            # Check if already running first
            if self.droplet_controller.running:
                logger.warning("Detection already running")
                self.socketio.emit(
                    "droplet:error",
                    {"message": "Detection is already running. Stop it first to restart."},
                )
                return

            # Check if ROI is set
            if (
                not hasattr(self.droplet_controller, "camera")
                or self.droplet_controller.camera.get_roi() is None
            ):
                logger.warning("ROI not set")
                self.socketio.emit(
                    "droplet:error",
                    {
                        "message": "ROI not set. Please select a region of interest in the Camera View tab first."
                    },
                )
                return

            success = self.droplet_controller.start()
            if success:
                logger.info("Droplet detection started via WebSocket")
                self._emit_status()
            else:
                logger.warning("Failed to start droplet detection")
                self.socketio.emit(
                    "droplet:error",
                    {"message": "Failed to start detection. Check ROI is set and valid."},
                )
        except Exception as e:
            logger.error(f"Error starting droplet detection: {e}", exc_info=True)
            self.socketio.emit("droplet:error", {"message": f"Error starting detection: {str(e)}"})

    def _handle_stop_command(self) -> None:
        """Handle stop command."""
        self.droplet_controller.stop()
        logger.info("Droplet detection stopped via WebSocket")
        self._emit_status()

    def _handle_config_command(self, params: Dict[str, Any]) -> None:
        """Handle config command."""
        success = self.droplet_controller.update_config(params)
        if success:
            logger.info("Droplet detection configuration updated")
            self.socketio.emit("droplet:config_updated", {"success": True})
        else:
            self.socketio.emit("droplet:error", {"message": "Failed to update configuration"})

    def _handle_profile_command(self, params: Dict[str, Any]) -> None:
        """Handle profile command."""
        profile_path = params.get("path")
        if not profile_path:
            self.socketio.emit("droplet:error", {"message": "Profile path not provided"})
            return

        try:
            success = self.droplet_controller.load_profile(profile_path)
            if success:
                logger.info(f"Profile loaded: {profile_path}")
                self.socketio.emit(
                    "droplet:profile_loaded", {"success": True, "path": profile_path}
                )
            else:
                self.socketio.emit(
                    "droplet:error", {"message": f"Failed to load profile: {profile_path}"}
                )
        except Exception as e:
            logger.error(f"Error loading profile {profile_path}: {e}")
            self.socketio.emit("droplet:error", {"message": f"Error loading profile: {str(e)}"})

    def _handle_reset_command(self) -> None:
        """Handle reset command."""
        self.droplet_controller.reset()
        logger.info("Droplet detection reset via WebSocket")
        self._emit_status()

    def handle_droplet_command(self, data: Dict[str, Any]) -> None:
        """
        Handle droplet detection command.

        Commands:
        - start: Start droplet detection
        - stop: Stop droplet detection
        - config: Update configuration
        - profile: Load parameter profile
        - get_status: Get current status
        - reset: Reset detection statistics

        Args:
            data: Dictionary containing 'cmd' and optional 'parameters' keys
        """
        try:
            cmd = data.get("cmd")
            if cmd is None:
                cmd = ""
            params = data.get("parameters", {})

            command_handlers: Dict[str, Callable[[], None]] = {
                "start": self._handle_start_command,
                "stop": self._handle_stop_command,
                "config": lambda: self._handle_config_command(params),
                "profile": lambda: self._handle_profile_command(params),
                "get_status": self._emit_status,
                "reset": self._handle_reset_command,
            }

            handler = command_handlers.get(cmd)
            if handler:
                handler()
            else:
                logger.warning(f"Unknown droplet command: {cmd}")
                self.socketio.emit("droplet:error", {"message": f"Unknown command: {cmd}"})

        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"Error handling droplet command: {e}")
            logger.debug(f"Command data: {data}")
            self.socketio.emit("droplet:error", {"message": f"Error processing command: {str(e)}"})

    def _emit_status(self) -> None:
        """Emit current detection status."""
        status = {
            "running": self.droplet_controller.running,
            "frame_count": self.droplet_controller.frame_count,
            "droplet_count_total": self.droplet_controller.droplet_count_total,
            "processing_rate_hz": getattr(self.droplet_controller, "processing_rate_hz", 0.0),
        }
        self.socketio.emit("droplet:status", status)

        # Also force emit histogram and statistics when status is requested
        # Always emit (even if not running) so UI shows current state
        self.emit_histogram(force=True)
        self.emit_statistics(force=True)

    def emit_histogram(self, force: bool = False) -> None:
        """
        Emit histogram data (with rate limiting).

        Args:
            force: If True, emit regardless of rate limit
        """
        now = time.time()
        last_emit = self.last_emit_time.get("histogram", 0)
        interval = self.emit_intervals["histogram"]

        if force or (now - last_emit) >= interval:
            try:
                histogram_data = self.droplet_controller.get_histogram()
                # Always emit histogram data (even if empty) when forced (e.g., get_status)
                # Otherwise only emit if detection is running and has data
                if force or (
                    hasattr(self.droplet_controller, "running") and self.droplet_controller.running
                ):
                    if histogram_data:
                        self.socketio.emit("droplet:histogram", histogram_data)
                        self.last_emit_time["histogram"] = now
                        # Log once per histogram refresh (every ~2 seconds)
                        count = histogram_data.get("count", 0)
                        frame_count = self.droplet_controller.frame_count
                        droplet_count = self.droplet_controller.droplet_count_total
                        logger.info(
                            f"Histogram update: frame={frame_count}, droplets={droplet_count}, histogram_count={count}"
                        )
            except Exception as e:
                logger.error(f"Error emitting histogram: {e}", exc_info=True)

    def emit_statistics(self, force: bool = False) -> None:
        """
        Emit statistics data (with rate limiting).

        Args:
            force: If True, emit regardless of rate limit
        """
        now = time.time()
        last_emit = self.last_emit_time.get("statistics", 0)
        interval = self.emit_intervals["statistics"]

        if force or (now - last_emit) >= interval:
            try:
                stats = self.droplet_controller.get_statistics()
                # Always emit statistics when forced (e.g., get_status)
                # Otherwise only emit if detection is running
                if force or (
                    hasattr(self.droplet_controller, "running") and self.droplet_controller.running
                ):
                    if stats:
                        self.socketio.emit("droplet:statistics", stats)
                        self.last_emit_time["statistics"] = now
                        # Don't log statistics separately - already logged with histogram
            except Exception as e:
                logger.error(f"Error emitting statistics: {e}", exc_info=True)

    def emit_performance(self, force: bool = False) -> None:
        """
        Emit performance metrics (with rate limiting, debug only).

        Args:
            force: If True, emit regardless of rate limit
        """
        now = time.time()
        last_emit = self.last_emit_time.get("performance", 0)
        interval = self.emit_intervals["performance"]

        if force or (now - last_emit) >= interval:
            try:
                perf = self.droplet_controller.get_performance_metrics()
                self.socketio.emit("droplet:performance", perf)
                self.last_emit_time["performance"] = now
            except Exception as e:
                logger.error(f"Error emitting performance: {e}")
