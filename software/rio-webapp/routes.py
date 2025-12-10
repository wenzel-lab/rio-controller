"""
Flask route handlers for the Rio microfluidics controller web application.

This module contains all HTTP route handlers, keeping route definitions
separate from application initialization and business logic.

Routes:
    /: Main page with device status
    /video: MJPEG video stream
"""

import time
import logging
import sys
import os
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
from typing import List, Any

# Add parent directory to path for imports
software_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if software_root not in sys.path:
    sys.path.insert(0, software_root)

logger = logging.getLogger(__name__)


def register_routes(
    app: Flask, socketio: SocketIO, view_model, heaters: List[Any], flow, cam, debug_data: dict
) -> None:
    """
    Register all Flask routes and WebSocket handlers.

    Args:
        app: Flask application instance
        socketio: Flask-SocketIO instance
        view_model: ViewModel instance for data formatting
        heaters: List of heater device controllers
        flow: Flow device controller
        cam: Camera device controller
        debug_data: Dictionary for debug information (mutated)
    """
    _register_http_routes(app, view_model, heaters, flow, cam, debug_data)
    _register_websocket_handlers(socketio)


def _register_http_routes(
    app: Flask, view_model, heaters: List[Any], flow, cam, debug_data: dict
) -> None:
    """Register HTTP routes."""

    @app.route("/")
    def index():
        """
        Main page route handler.

        Renders the main template with current device state.
        """
        try:
            debug_data["update_count"] += 1

            # Format data for template using view model
            heaters_data = view_model.format_heater_data(heaters)
            flows_data = view_model.format_flow_data(flow)
            camera_data = view_model.format_camera_data(cam)
            strobe_data = view_model.format_strobe_data(cam)
            debug_formatted = view_model.format_debug_data(debug_data["update_count"])

            return render_template(
                "index.html",
                debug=debug_formatted,
                strobe=strobe_data,
                heaters=heaters_data,
                flows=flows_data,
                cam=camera_data,
            )
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            import traceback

            traceback.print_exc()
            return f"<html><body><h1>Error</h1><pre>{str(e)}</pre></body></html>", 500

    @app.route("/video")
    def video():
        """
        Video stream route handler.

        Returns MJPEG stream of camera feed, or 404 if camera is disabled.
        """
        if cam.cam_data.get("camera") == "none":
            return Response("Camera disabled", status=404, mimetype="text/plain")

        def generate_frames():
            """Generator for MJPEG frames."""
            while True:
                frame = cam.get_frame()
                if frame:
                    yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                else:
                    time.sleep(0.1)

        return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


def _register_websocket_handlers(socketio: SocketIO) -> None:
    """Register WebSocket event handlers."""

    @socketio.on("connect")
    def handle_connect():
        """Handle WebSocket client connection."""
        logger.info("WebSocket client connected")

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle WebSocket client disconnection."""
        logger.info("WebSocket client disconnected")


def create_background_update_task(
    socketio: SocketIO, view_model, heaters: List[Any], flow, cam, debug_data: dict
):
    """
    Create and return a background update task function.

    This function is designed to be passed to socketio.start_background_task().
    It periodically updates device data and emits to WebSocket clients.

    Args:
        socketio: Flask-SocketIO instance
        view_model: ViewModel instance for data formatting
        heaters: List of heater device controllers
        flow: Flow device controller
        cam: Camera device controller
        debug_data: Dictionary for debug information (mutated)

    Returns:
        Function that can be used as a background task
    """

    def background_update_loop():
        """
        Background thread loop for periodic data updates.

        Updates device data and emits to WebSocket clients at regular intervals.
        Uses ViewModel to format data for clients.
        """
        while True:
            try:
                time.sleep(1.0)
                debug_data["update_count"] += 1

                # Update hardware device controllers
                cam.update_strobe_data()
                for heater in heaters:
                    heater.update()
                flow.update()

                # Format data for clients
                heaters_data = view_model.format_heater_data(heaters)
                flows_data = view_model.format_flow_data(flow)
                camera_data = view_model.format_camera_data(cam)
                strobe_data = view_model.format_strobe_data(cam)
                debug_formatted = view_model.format_debug_data(debug_data["update_count"])

                # Emit updates to all connected clients
                socketio.emit("heaters", heaters_data)
                socketio.emit("flows", flows_data)
                socketio.emit("cam", camera_data)
                socketio.emit("strobe", strobe_data)
                socketio.emit("debug", debug_formatted)
            except Exception as e:
                logger.error(f"Error in background update loop: {e}")
                time.sleep(1.0)

    return background_update_loop
