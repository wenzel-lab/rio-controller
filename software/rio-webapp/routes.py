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
from typing import List, Any, Optional

# Add parent directory to path for imports
software_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if software_root not in sys.path:
    sys.path.insert(0, software_root)

logger = logging.getLogger(__name__)


def register_routes(
    app: Flask,
    socketio: SocketIO,
    view_model,
    heaters: List[Any],
    flow,
    cam,
    debug_data: dict,
    droplet_controller: Optional[Any] = None,
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
        droplet_controller: Optional DropletDetectorController instance
    """
    # Pass droplet_controller availability to template
    app.jinja_env.globals["droplet_analysis_enabled"] = droplet_controller is not None

    _register_http_routes(app, view_model, heaters, flow, cam, debug_data, droplet_controller)
    _register_websocket_handlers(socketio)


def _handle_route_error(e: Exception, route_name: str):
    """Handle route errors consistently."""
    from flask import jsonify

    logger.error(f"Error in {route_name}: {e}")
    return jsonify({"error": str(e)}), 500


def _register_droplet_status_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet status route."""
    from flask import jsonify

    @app.route("/api/droplet/status", methods=["GET"])
    def droplet_status():
        """Get droplet detection status."""
        try:
            return jsonify(
                {
                    "running": droplet_controller.running,
                    "frame_count": droplet_controller.frame_count,
                    "droplet_count_total": droplet_controller.droplet_count_total,
                    "processing_rate_hz": round(
                        getattr(droplet_controller, "processing_rate_hz", 0.0), 2
                    ),
                    "statistics": droplet_controller.get_statistics(),
                }
            )
        except Exception as e:
            return _handle_route_error(e, "droplet_status")


def _register_droplet_histogram_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet histogram route."""
    from flask import jsonify

    @app.route("/api/droplet/histogram", methods=["GET"])
    def droplet_histogram():
        """Get current histogram data."""
        try:
            return jsonify(droplet_controller.get_histogram())
        except Exception as e:
            return _handle_route_error(e, "droplet_histogram")


def _register_droplet_statistics_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet statistics route."""
    from flask import jsonify

    @app.route("/api/droplet/statistics", methods=["GET"])
    def droplet_statistics():
        """Get current statistics."""
        try:
            return jsonify(droplet_controller.get_statistics())
        except Exception as e:
            return _handle_route_error(e, "droplet_statistics")


def _register_droplet_performance_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet performance route."""
    from flask import jsonify

    @app.route("/api/droplet/performance", methods=["GET"])
    def droplet_performance():
        """Get performance timing metrics."""
        try:
            return jsonify(droplet_controller.get_performance_metrics())
        except Exception as e:
            return _handle_route_error(e, "droplet_performance")


def _register_droplet_status_routes(app: Flask, droplet_controller: Any) -> None:
    """Register all droplet status API routes."""
    _register_droplet_status_route(app, droplet_controller)
    _register_droplet_histogram_route(app, droplet_controller)
    _register_droplet_statistics_route(app, droplet_controller)
    _register_droplet_performance_route(app, droplet_controller)


def _register_droplet_control_routes(app: Flask, droplet_controller: Any) -> None:
    """Register droplet control API routes."""
    from flask import jsonify

    @app.route("/api/droplet/start", methods=["POST"])
    def droplet_start():
        """Start droplet detection."""
        try:
            success = droplet_controller.start()
            if success:
                return jsonify({"success": True, "message": "Detection started"})
            return (
                jsonify({"success": False, "message": "Failed to start. Check ROI is set."}),
                400,
            )
        except Exception as e:
            return _handle_route_error(e, "droplet_start")

    @app.route("/api/droplet/stop", methods=["POST"])
    def droplet_stop():
        """Stop droplet detection."""
        try:
            droplet_controller.stop()
            return jsonify({"success": True, "message": "Detection stopped"})
        except Exception as e:
            return _handle_route_error(e, "droplet_stop")


def _register_droplet_config_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet config route."""
    from flask import jsonify, request

    @app.route("/api/droplet/config", methods=["POST"])
    def droplet_config():
        """Update droplet detection configuration."""
        try:
            config_data = request.get_json()
            if not config_data:
                return jsonify({"error": "No configuration data provided"}), 400

            success = droplet_controller.update_config(config_data)
            if success:
                return jsonify({"success": True, "message": "Configuration updated"})
            return (
                jsonify({"success": False, "message": "Failed to update configuration"}),
                400,
            )
        except Exception as e:
            return _handle_route_error(e, "droplet_config")


def _register_droplet_profile_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet profile route."""
    from flask import jsonify, request

    @app.route("/api/droplet/profile", methods=["POST"])
    def droplet_profile():
        """Load parameter profile."""
        try:
            data = request.get_json()
            if not data or "path" not in data:
                return jsonify({"error": "Profile path not provided"}), 400

            success = droplet_controller.load_profile(data["path"])
            if success:
                return jsonify({"success": True, "message": f"Profile loaded: {data['path']}"})
            return (
                jsonify({"success": False, "message": f"Failed to load profile: {data['path']}"}),
                400,
            )
        except Exception as e:
            return _handle_route_error(e, "droplet_profile")


def _register_droplet_config_routes(app: Flask, droplet_controller: Any) -> None:
    """Register all droplet configuration API routes."""
    _register_droplet_config_route(app, droplet_controller)
    _register_droplet_profile_route(app, droplet_controller)


def _register_droplet_export_route(app: Flask, droplet_controller: Any) -> None:
    """Register droplet export route."""
    from flask import Response, request

    @app.route("/api/droplet/export", methods=["GET"])
    def droplet_export():
        """Export droplet measurements as CSV or TXT."""
        try:
            format_type = request.args.get("format", "csv").lower()

            if format_type not in ["csv", "txt"]:
                from flask import jsonify

                return jsonify({"error": "Format must be 'csv' or 'txt'"}), 400

            export_data = droplet_controller.export_data(format_type)

            if export_data is None:
                from flask import jsonify

                return jsonify({"error": "No data available for export"}), 404

            # Generate filename with timestamp
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"droplet_measurements_{timestamp}.{format_type}"

            # Set appropriate MIME type
            mimetype = "text/csv" if format_type == "csv" else "text/plain"

            return Response(
                export_data,
                mimetype=mimetype,
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        except Exception as e:
            return _handle_route_error(e, "droplet_export")


def _register_droplet_api_routes(app: Flask, droplet_controller: Any) -> None:
    """Register all droplet detection API routes."""
    _register_droplet_status_routes(app, droplet_controller)
    _register_droplet_control_routes(app, droplet_controller)
    _register_droplet_config_routes(app, droplet_controller)
    _register_droplet_export_route(app, droplet_controller)


def _register_http_routes(
    app: Flask,
    view_model,
    heaters: List[Any],
    flow,
    cam,
    debug_data: dict,
    droplet_controller: Optional[Any] = None,
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

            # Determine if flow and heater tabs should be shown
            # Check if controllers exist and have data
            # Also check environment variables for explicit enable/disable
            import os

            flow_enabled_env = os.getenv("RIO_FLOW_ENABLED", "").lower()
            heater_enabled_env = os.getenv("RIO_HEATER_ENABLED", "").lower()

            # If environment variable is explicitly set, use it
            if flow_enabled_env == "false":
                flow_enabled = False
            elif flow_enabled_env == "true":
                flow_enabled = True
            else:
                # Default: check if controllers exist and have data
                flow_enabled = flow is not None and len(flows_data) > 0

            if heater_enabled_env == "false":
                heater_enabled = False
            elif heater_enabled_env == "true":
                heater_enabled = True
            else:
                # Default: check if controllers exist and have data
                heater_enabled = heaters is not None and len(heaters) > 0 and len(heaters_data) > 0

            return render_template(
                "index.html",
                debug=debug_formatted,
                strobe=strobe_data,
                heaters=heaters_data,
                flows=flows_data,
                cam=camera_data,
                flow_enabled=flow_enabled,
                heater_enabled=heater_enabled,
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
        Implements frame rate limiting for display to reduce Pi load.
        Lazy initialization: starts camera thread only when first client connects.
        """
        if cam.cam_data.get("camera") == "none":
            return Response("Camera disabled", status=404, mimetype="text/plain")

        # Lazy initialization: start camera thread only when first client connects
        # This reduces startup overhead and CPU usage when no clients are viewing
        if cam.thread is None or not cam.thread.is_alive():
            cam.initialize()

        # Get display FPS from config (default 10 fps to reduce Pi load)
        from config import CAMERA_DISPLAY_FPS

        display_fps = cam.cam_data.get("display_fps", CAMERA_DISPLAY_FPS)
        frame_interval = 1.0 / float(display_fps) if display_fps > 0 else 0.1

        def generate_frames():
            """Generator for MJPEG frames with frame rate limiting."""
            import time

            last_frame_time = 0.0
            while True:
                current_time = time.time()
                # Only yield frame if enough time has passed (frame rate limiting)
                if current_time - last_frame_time >= frame_interval:
                    frame = cam.get_frame()
                    if frame:
                        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
                        last_frame_time = current_time
                    else:
                        time.sleep(0.1)
                else:
                    # Sleep briefly to avoid busy waiting
                    time.sleep(0.01)

        response = Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
        # Add headers to prevent caching of live video stream and allow CORS
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # CORS header - allow cross-origin access if needed (can be made more restrictive)
        # For local network use, '*' is acceptable; for production, consider restricting
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    # Droplet detection API routes
    if droplet_controller is not None:
        _register_droplet_api_routes(app, droplet_controller)


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
    socketio: SocketIO,
    view_model,
    heaters: List[Any],
    flow,
    cam,
    debug_data: dict,
    droplet_web_controller: Optional[Any] = None,
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

                # Emit droplet detection updates (if controller available and running)
                if droplet_web_controller is not None:
                    try:
                        # Only emit if detection is actually running
                        if (
                            hasattr(droplet_web_controller, "droplet_controller")
                            and hasattr(droplet_web_controller.droplet_controller, "running")
                            and droplet_web_controller.droplet_controller.running
                        ):
                            droplet_web_controller.emit_histogram()
                            droplet_web_controller.emit_statistics()
                    except Exception as e:
                        # Don't break background loop if droplet detection has issues
                        logger.debug(f"Error in droplet update loop: {e}")
            except Exception as e:
                logger.error(f"Error in background update loop: {e}")
                time.sleep(1.0)

    return background_update_loop
