"""
Main Flask application entry point for Rio microfluidics controller.

This module follows MVC architecture:
- Model: Hardware access classes (PiFlow, PiStrobe, Camera, etc.)
- View: Templates and static files (HTML, JavaScript, CSS)
- Controller: Request handlers and WebSocket event handlers

The application is refactored to separate concerns:
- Controllers handle business logic and coordinate between models and views
- ViewModel formats data for template rendering
- Models handle hardware communication
- Views handle presentation

Usage:
    python pi_webapp.py [PORT]
    
    Or set RIO_PORT environment variable for port number.
"""

import time
import os
import sys
import logging
from threading import Event
from flask import Flask, render_template, Response
from flask_socketio import SocketIO
import eventlet
import picommon
from piholder_web import heater_web
from camera_pi import Camera
from piflow_web import FlowWeb
from controllers import CameraController, FlowController, HeaterController, ViewModel

# Configure eventlet monkey patching
eventlet.monkey_patch(os=True, select=True, socket=True, thread=False, time=True, psycopg=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
exit_event = Event()
debug_data = {'update_count': 0}

# Initialize hardware communication
logger.info("Initializing SPI communication...")
picommon.spi_init(0, 2, 30000)

# Initialize hardware models
logger.info("Initializing hardware models...")
heater1 = heater_web(1, picommon.PORT_HEATER1)
heater2 = heater_web(2, picommon.PORT_HEATER2)
heater3 = heater_web(3, picommon.PORT_HEATER3)
heater4 = heater_web(4, picommon.PORT_HEATER4)
heaters = [heater1, heater2, heater3, heater4]

flow = FlowWeb(picommon.PORT_FLOW)
cam = Camera(exit_event, None)  # SocketIO will be set after app creation

# Initialize Flask application
app = Flask(__name__, static_folder='static', static_url_path='/static')
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')

# Set socketio in camera (needed for WebSocket handlers)
cam.socketio = socketio
# Re-register handlers now that socketio is set
cam._register_websocket_handlers()

# Initialize controllers
logger.info("Initializing controllers...")
camera_controller = CameraController(cam, socketio)
flow_controller = FlowController(flow, socketio)
heater_controller = HeaterController(heaters, socketio)

# Initialize view model
view_model = ViewModel()

# Background update thread
update_thread = None


def update_all_data() -> None:
    """
    Update all device data from hardware.
    
    This function coordinates data updates from all hardware models
    and prepares data for view rendering.
    """
    try:
        cam.update_strobe_data()
        
        # Update heaters
        for heater in heaters:
            heater.update()
        
        # Update flow
        flow.update()
        
    except Exception as e:
        logger.error(f"Error updating device data: {e}")


def background_update_loop() -> None:
    """
    Background thread loop for periodic data updates.
    
    Updates device data and emits to WebSocket clients at regular intervals.
    """
    while True:
        try:
            time.sleep(1.0)
            debug_data['update_count'] += 1
            update_all_data()
            
            # Format data using view model
            heaters_data = view_model.format_heater_data(heaters)
            flows_data = view_model.format_flow_data(flow)
            debug_formatted = view_model.format_debug_data(debug_data['update_count'])
            
            # Emit updated data to all clients
            socketio.emit('debug', debug_formatted)
            socketio.emit('heaters', heaters_data)
            socketio.emit('flows', flows_data)
            cam.emit()
            
        except Exception as e:
            logger.error(f"Error in background update loop: {e}")


def start_background_thread() -> None:
    """Start the background data update thread."""
    global update_thread
    if update_thread is None:
        update_thread = socketio.start_background_task(target=background_update_loop)
        logger.info("Background update thread started")


@app.route('/')
def index():
    """
    Main page route handler.
    
    Renders the main template with current device state.
    """
    try:
        debug_data['update_count'] += 1
        
        # Format data for template using view model
        heaters_data = view_model.format_heater_data(heaters)
        flows_data = view_model.format_flow_data(flow)
        camera_data = view_model.format_camera_data(cam)
        strobe_data = view_model.format_strobe_data(cam)
        debug_formatted = view_model.format_debug_data(debug_data['update_count'])
        
        return render_template(
            'index.html',
            debug=debug_formatted,
            strobe=strobe_data,
            heaters=heaters_data,
            flows=flows_data,
            cam=camera_data
        )
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        import traceback
        traceback.print_exc()
        return f"<html><body><h1>Error</h1><pre>{str(e)}</pre></body></html>", 500


@app.route('/video')
def video():
    """
    Video stream route handler.
    
    Returns MJPEG stream of camera feed, or 404 if camera is disabled.
    """
    if cam.cam_data.get('camera') == 'none':
        return Response('Camera disabled', status=404, mimetype='text/plain')
    
    def generate_frames():
        """Generator for MJPEG frames."""
        while True:
            frame = cam.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@socketio.on('connect')
def on_connect():
    """Handle WebSocket client connection."""
    logger.info("WebSocket client connected")
    start_background_thread()


@socketio.on('disconnect')
def on_disconnect():
    """Handle WebSocket client disconnection."""
    logger.info("WebSocket client disconnected")


if __name__ == '__main__':
    # Parse command line arguments
    port = int(os.getenv('RIO_PORT', '5000'))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Invalid port number: {sys.argv[1]}, using default: {port}")
    
    logger.info(f"Starting Rio microfluidics controller on port {port}...")
    logger.info(f"If port is in use, kill the process with: lsof -ti:{port} | xargs kill -9")
    logger.info(f"Or use a different port: python pi_webapp.py <PORT_NUMBER>")
    
    # Initialize data before starting server
    update_all_data()
    
    # Start server
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=True, use_reloader=False)
    finally:
        exit_event.set()
        logger.info("Server shutting down...")

