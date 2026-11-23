import os
import json
import time
import threading
from flask import Flask, jsonify, send_file, request, make_response, Response
from flask_cors import CORS
import eventlet
from camera_pi import Camera
import picommon
import atexit
import RPi.GPIO as GPIO
import glob
from datetime import datetime
from threading import Event
from piflow_web import flow_web

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create a dummy exit event
exit_event = Event()

# Initialize SPI for sensors and actuators
picommon.spi_init(0, 2, 500000)   # 500 kHz as in Pierre's flow_sensor_acquisition_v4.py (was 30 kHz: ~6 ms per packet round trip)

# Global camera instance
camera = None

# Global flow controller instance
flow_controller = None
flow_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Continuous flow sampler (added 2026-11-02)
#
# The PIC services one SPI packet per main-loop cycle (ADC_PERIOD_MS = 8 ms on
# the firmware currently flashed), so reply_pause_s must be >= that period.
# update() issues two queries (pressure + flow) -> ~27 Hz max, same as
# flow_sensor_acquisition_v4.py.  The LG16 at 16-bit resolution delivers a new
# value only every ~74 ms (~11-13 Hz); faster samples repeat the last value.
# Sampling runs in ONE background thread so HTTP clients never drive SPI timing;
# clients read the ring buffer via /api/flow/history.
# ---------------------------------------------------------------------------
from collections import deque
import itertools

FLOW_PIC_REPLY_PAUSE_S = 0.006          # PIC answers within its main-loop iteration; measured OK at 6 ms
FLOW_SAMPLE_RATE_HZ    = 100.0          # legacy per-sample polling (firmware < 3.2): target; actual rate is reported
FLOW_HISTORY_SECONDS   = 1800           # ring buffer length
FLOW_PRESSURE_EVERY_N  = 5              # legacy mode: full update (pressure + flow) every N cycles
# v3.2 batch mode (firmware >= 3.2): the PIC keeps an indexed ring of accepted readings
# and we fetch them in batches, so no reading is lost or duplicated regardless of Pi timing.
FLOW_BATCH_POLL_HZ     = 20.0           # batches per second per channel (16 samples max each)
FLOW_BATCH_DRAIN_MAX   = 8              # extra back-to-back batches when the PIC has more queued
FLOW_PRESSURE_PERIOD_S = 1.0            # pressure readout period in batch mode
FLOW_HISTORY_MAX       = 220000         # ~1800 s at 13 bit (112/s)

flow_history = deque(maxlen=FLOW_HISTORY_MAX)
flow_history_counter = itertools.count(1)   # monotonic index 'i' of every stored sample (batch mode: 't' is
                                            # estimated and not strictly monotonic, clients must page by 'i')
flow_sampler_thread = None
flow_sampler_stats = {
    'running': False,
    'mode': None,               # 'batch' (fw >= 3.2) or 'poll' (legacy)
    'firmware': None,
    'channels': [],             # channels with a sensor (batch mode)
    'target_hz': FLOW_SAMPLE_RATE_HZ,
    'actual_hz': 0.0,           # poll mode: cycles/s; batch mode: unique samples/s
    'cycles': 0,
    'samples': 0,               # batch mode: unique samples stored
    'gaps': 0,                  # batch mode: sequence discontinuities seen
    'gap_samples': 0,           # batch mode: readings the PIC had already overwritten
    'batch_errors': 0,          # batch mode: SPI queries without a valid reply (retried)
    'errors': 0,
    'last_error': None,
    'started_at': None,
}


def _flow_snapshot(now):
    """Build one history sample from the flow controller's current state."""
    fc = flow_controller
    n = fc.flow.NUM_CONTROLLERS
    flows = []
    pressures = []
    for i in range(n):
        try:
            flows.append(float(fc.flow_ul_hr_text[i]))
        except (ValueError, TypeError):
            flows.append(None)
        try:
            pressures.append(float(str(fc.pressure_mbar_text[i]).split('/')[0]))
        except (ValueError, TypeError, IndexError):
            pressures.append(None)
    return {
        't': now,
        'flow_ul_hr': flows,
        'pressure_mbar': pressures,
        'status': list(fc.status_text),
        'control_mode': list(fc.control_modes_text),
        'fluid_type': list(fc.fluid_types),
        'refresh_counter': getattr(fc.flow, 'flow_refresh_counter', None),
    }


def _flow_sampler_loop():
    """Deadline-based loop: SPI update -> append to ring buffer."""
    interval = 1.0 / FLOW_SAMPLE_RATE_HZ
    next_deadline = time.perf_counter()
    t0 = time.perf_counter()
    cycles = 0
    flow_sampler_stats['running'] = True
    flow_sampler_stats['started_at'] = time.time()
    while flow_sampler_stats['running']:
        try:
            with flow_lock:
                flow_controller.update(flows_only=(cycles % FLOW_PRESSURE_EVERY_N != 0))
                sample = _flow_snapshot(time.time())
            sample['i'] = next(flow_history_counter)
            flow_history.append(sample)
        except Exception as e:
            flow_sampler_stats['errors'] += 1
            flow_sampler_stats['last_error'] = str(e)
        cycles += 1
        flow_sampler_stats['cycles'] = cycles
        if cycles % 50 == 0:
            flow_sampler_stats['actual_hz'] = round(cycles / (time.perf_counter() - t0), 2)
        next_deadline += interval
        slack = next_deadline - time.perf_counter()
        if slack > 0:
            time.sleep(slack)
        else:
            next_deadline = time.perf_counter()  # overran; don't busy-spin to catch up


def _flow_batch_sampler_loop(channels, since):
    """Firmware >= 3.2: fetch indexed batches; every accepted reading is stored once.

    Per sample we store the PIC sequence number and PIC millisecond timestamp, plus a
    Pi-side time estimate: t = poll time - age of the sample relative to the newest one
    in the same batch (the newest is at most one PIC iteration old).  The PIC clock
    runs from its internal RC oscillator (~1 %): use 't_pic_ms' for intervals within a
    run and 't' for wall-clock alignment.
    """
    fc = flow_controller
    flow = fc.flow
    n_ctrl = flow.NUM_CONTROLLERS
    interval = 1.0 / FLOW_BATCH_POLL_HZ
    next_deadline = time.perf_counter()
    t0 = time.perf_counter()
    next_pressure = 0.0
    pressures = [None] * n_ctrl
    stats = flow_sampler_stats
    stats['running'] = True
    stats['started_at'] = time.time()
    while stats['running']:
        try:
            now = time.time()
            if now >= next_pressure:
                with flow_lock:
                    fc.update()                       # pressure + legacy flow text
                for i in range(n_ctrl):
                    try:
                        pressures[i] = float(str(fc.pressure_mbar_text[i]).split('/')[0])
                    except (ValueError, TypeError, IndexError):
                        pressures[i] = None
                next_pressure = now + FLOW_PRESSURE_PERIOD_S

            for chan in channels:
                for _ in range(1 + FLOW_BATCH_DRAIN_MAX):
                    with flow_lock:
                        ok, b = flow.get_flow_batch(chan, since[chan])
                    t_poll = time.time()
                    if not ok:
                        stats['batch_errors'] += 1
                        break                          # idempotent: retried next cycle
                    expected = (since[chan] + 1) & 0xFFFF
                    if b['err'] == flow.ERR_FLOW_BATCH_GAP or (b['n'] and b['seq0'] != expected):
                        stats['gaps'] += 1
                        lost = (b['seq0'] - expected) & 0xFFFF
                        if lost < 0x8000:               # overwritten readings; a PIC reset gives a bogus count
                            stats['gap_samples'] += lost
                        # resync even when the PIC has nothing yet (e.g. right after a reset)
                        since[chan] = (b['seq0'] - 1) & 0xFFFF
                    if b['n'] == 0:
                        break
                    scale = b['scale'] or 1
                    t_head = b['samples'][-1][1]
                    for seq, t_ms, raw in b['samples']:
                        age_s = ((t_head - t_ms) & 0xFFFF) / 1000.0
                        flows = [None] * n_ctrl
                        flows[chan] = raw * 60.0 / scale
                        flow_history.append({
                            'i': next(flow_history_counter),
                            't': t_poll - age_s,
                            'chan': chan,
                            'seq': seq,
                            't_pic_ms': t_ms,
                            'flow_raw': raw,
                            'flow_ul_hr': flows,
                            'pressure_mbar': list(pressures),
                            'status': list(fc.status_text),
                            'refresh_counter': seq,       # legacy consumers: changes per new sample
                        })
                    since[chan] = b['samples'][-1][0]
                    stats['samples'] += b['n']
                    if b['n'] < flow.FLOW_BATCH_MAX_SAMPLES:
                        break
        except Exception as e:
            stats['errors'] += 1
            stats['last_error'] = str(e)
        stats['cycles'] += 1
        if stats['cycles'] % 20 == 0:
            stats['actual_hz'] = round(stats['samples'] / (time.perf_counter() - t0), 2)
        next_deadline += interval
        slack = next_deadline - time.perf_counter()
        if slack > 0:
            time.sleep(slack)
        else:
            next_deadline = time.perf_counter()


def _flow_detect_batch_channels():
    """Return ({chan: ok_count}, firmware) for channels that have accepted readings, or None if fw < 3.2."""
    flow = flow_controller.flow
    fw = None
    for _ in range(3):
        with flow_lock:
            ok, fw = flow.get_fw_version()
        if ok:
            break
        time.sleep(0.05)
    if not ok or fw < (3, 2):
        return None, fw
    since = {}
    for chan in range(flow.NUM_CONTROLLERS):
        for _ in range(3):
            with flow_lock:
                ok, st = flow.get_flow_stats(chan)
            if ok:
                break
            time.sleep(0.05)
        if ok and st['ok'] > 0:
            since[chan] = st['ok'] & 0xFFFF
    return since, fw


def start_flow_sampler():
    global flow_sampler_thread
    if flow_controller is None:
        return False
    if flow_sampler_thread is not None and flow_sampler_thread.is_alive():
        return True
    flow_controller.flow.reply_pause_s = FLOW_PIC_REPLY_PAUSE_S
    since, fw = _flow_detect_batch_channels()
    flow_sampler_stats['firmware'] = list(fw) if fw else None
    if since:
        flow_sampler_stats['mode'] = 'batch'
        flow_sampler_stats['channels'] = sorted(since)
        flow_sampler_stats['target_hz'] = None
        flow_sampler_thread = threading.Thread(target=_flow_batch_sampler_loop, args=(sorted(since), since),
                                               name='flow-sampler', daemon=True)
        print(f"Flow sampler started (batch mode, fw {fw}): channels {sorted(since)}, {FLOW_BATCH_POLL_HZ} batches/s")
    else:
        flow_sampler_stats['mode'] = 'poll'
        flow_sampler_thread = threading.Thread(target=_flow_sampler_loop, name='flow-sampler', daemon=True)
        print(f"Flow sampler started (poll mode, fw {fw}): target {FLOW_SAMPLE_RATE_HZ} Hz, reply_pause {FLOW_PIC_REPLY_PAUSE_S}s")
    flow_sampler_thread.start()
    return True

# Initialize camera with proper settings
def init_camera():
    global camera
    if camera is None:
        # Create dummy socketio for the camera
        class DummySocketIO:
            def __init__(self):
                self.handlers = {}

            def emit(self, *args, **kwargs):
                print(f"SocketIO emit: {args} {kwargs}")

            def on(self, event, handler=None):
                print(f"SocketIO registering handler for: {event}")
                if handler is not None:
                    print(f"Registering handler: {handler.__name__ if hasattr(handler, '__name__') else 'lambda'}")
                    self.handlers[event] = handler
                else:
                    print("No handler provided, returning decorator")

                def decorator(f):
                    print(f"Registering decorated handler: {f.__name__ if hasattr(f, '__name__') else 'lambda'}")
                    self.handlers[event] = f
                    return f

                return decorator        
    
            def trigger(self, event, *args, **kwargs):
                if event in self.handlers:
                    return self.handlers[event](*args, **kwargs)

        dummy_socketio = DummySocketIO()
        
        # Initialize camera with proper exit event and socketio
        camera = Camera(exit_event, dummy_socketio)
        
        # Initialize with default settings
        camera.cam_data['camera'] = 'pi'  # Set to 'pi' to enable camera
        camera.on_cam({'cmd': 'select', 'parameters': {'camera': 'pi'}})
        
        # Initial strobe update
        camera.update_strobe_data()
        
        print("Camera and strobe initialized")
    return camera

# Global camera settings
current_settings = {
    'width': 1024,
    'height': 768,
    'fps': 49,
    'exposure_mode': 'auto',  # 'auto' or 'manual'
    'exposure_time_us': None  # Only used in manual mode
}

# Initialize flow controller
def init_flow_controller():
    """Initializes the global flow controller instance."""
    global flow_controller
    with flow_lock:
        if flow_controller is None:
            print("Initializing flow controller...")
            flow_controller = flow_web(picommon.PORT_FLOW)
            if not flow_controller.enabled:
                print("Flow controller initialization failed.")
                flow_controller = None  # Reset if initialization failed
            else:
                print("Flow controller initialized successfully.")
    if flow_controller is not None:
        start_flow_sampler()
    return flow_controller

# Update camera settings
def update_camera_settings(width=None, height=None, fps=None, exposure_mode=None, exposure_time_us=None):
    global current_settings
    
    # Update settings with provided values or use current values
    if width is not None:
        current_settings['width'] = width
    if height is not None:
        current_settings['height'] = height
    if fps is not None:
        current_settings['fps'] = fps
    if exposure_mode is not None:
        current_settings['exposure_mode'] = exposure_mode
    if exposure_time_us is not None:
        current_settings['exposure_time_us'] = exposure_time_us

    print(f"Applying camera settings - Width: {current_settings['width']}, Height: {current_settings['height']}, "
          f"FPS: {current_settings['fps']}, Exposure Mode: {current_settings['exposure_mode']}, "
          f"Exposure: {current_settings.get('exposure_time_us', 'auto')}µs")
    
    # Prepare camera settings
    cam_settings = {
        'cmd': 'init',
        'width': current_settings['width'],
        'height': current_settings['height'],
        'fps': current_settings['fps'],
        'exposure_mode': current_settings['exposure_mode']
    }
    
    # Only set exposure time if in manual mode and a value is provided
    if current_settings['exposure_mode'] == 'manual' and current_settings.get('exposure_time_us'):
        cam_settings['exposure_time_us'] = current_settings['exposure_time_us']
    
    # Apply settings
    camera.on_cam(cam_settings)
    
    return current_settings

# API Endpoints
@app.route('/api/camera/init', methods=['POST'])
def camera_init():
    try:
        init_camera()
        return jsonify({'status': 'success', 'message': 'Camera initialized'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/camera/settings', methods=['GET'])
def get_camera_settings():
    """Get current camera settings including resolution, FPS, and exposure time"""
    try:
        settings = update_camera_settings()  # This will initialize or update settings
        return jsonify({
            'status': 'success',
            'settings': {
                'width': settings['width'],
                'height': settings['height'],
                'fps': settings['fps'],
                'exposure_mode': settings['exposure_mode'],
                'exposure_time_us': settings.get('exposure_time_us')
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/camera/settings', methods=['POST'])
def update_camera_settings_endpoint():
    """Update camera settings (resolution, FPS, exposure mode, and/or exposure time)"""
    try:
        data = request.get_json()
        
        # Get new settings
        width = data.get('width')
        height = data.get('height')
        fps = data.get('fps')
        exposure_mode = data.get('exposure_mode')
        exposure_time_us = data.get('exposure_time_us')
        
        # Validate inputs
        if any(x is not None and (not isinstance(x, int) or x <= 0) for x in [width, height, fps, exposure_time_us] if x is not None):
            return jsonify({'status': 'error', 'message': 'Width, height, FPS, and exposure time must be positive integers'}), 400
        
        if exposure_mode is not None and exposure_mode not in ['auto', 'manual']:
            return jsonify({'status': 'error', 'message': 'Exposure mode must be either "auto" or "manual"'}), 400
        
        # This will update settings and apply them to the camera
        settings = update_camera_settings(
            width=width,
            height=height,
            fps=fps,
            exposure_mode=exposure_mode,
            exposure_time_us=exposure_time_us
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Camera settings updated',
            'settings': {
                'width': settings['width'],
                'height': settings['height'],
                'fps': settings['fps'],
                'exposure_mode': settings['exposure_mode'],
                'exposure_time_us': settings.get('exposure_time_us')
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/camera/capture', methods=['GET'])
def capture_image():
    try:
        init_camera()
        
        # Define the correct snapshots directory
        snapshots_dir = os.path.expanduser('/home/pi/webapp/snapshots')
        os.makedirs(snapshots_dir, exist_ok=True)
        
        # Capture a new frame
        frame = camera.get_frame()
        if frame is None:
            raise Exception("Failed to capture frame")
            
        # Generate filename with timestamp
        filename = f'snapshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        filepath = os.path.join(snapshots_dir, filename)
        
        # Save the image to the snapshots directory
        with open(filepath, 'wb') as f:
            f.write(frame)
        
        # For all requests, return the image directly
        response = make_response(frame)
        response.headers.set('Content-Type', 'image/jpeg')
        response.headers.set('Content-Disposition', 'attachment', filename=filename)
        return response
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/camera/stream')
def stream_frames():
    def generate():
        try:
            # Initialize camera for streaming
            init_camera()
            
            while True:
                # Capture frame to memory
                frame = camera.get_frame()
                if frame is None:
                    print("Failed to get frame")
                    continue
                    
                # Yield the frame in the HTTP response
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                
                # Control frame rate
                time.sleep(1/current_settings['fps'])  # Use the actual FPS setting
        except Exception as e:
            print(f"Stream error: {e}")
        finally:
            # Clean up camera resources when stream ends
            cleanup()
    
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/camera/exposure', methods=['GET'])
def get_exposure_time():
    """Get the current camera exposure time in microseconds"""
    try:
        if camera is None:
            init_camera()
        
        # Update the strobe data to get the latest exposure time
        camera.update_strobe_data()
        
        # Get the exposure time from the camera
        exposure_us = camera.camera.shutter_speed
        #exposure_us = camera.strobe_data.get('cam_shutter_speed_us', 0)
        
        return jsonify({
            'status': 'success',
            'exposure_time_us': exposure_us
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/strobe/settings', methods=['GET', 'POST'])
def handle_strobe_settings():
    """Get or update strobe settings"""
    try:
        if camera is None:
            init_camera()
            
        if request.method == 'GET':
            # Get current strobe settings
            camera.update_strobe_data()  # Ensure we have the latest data
            return jsonify({
                'status': 'success',
                'settings': {
                    'enabled': camera.strobe_data['enable'],
                    'hold': camera.strobe_data['hold'],
                    'period_ns': camera.strobe_data['period_ns'],
                    'wait_ns': camera.strobe_data.get('wait_ns', 0),
                    'framerate': camera.strobe_data.get('framerate', 0)
                }
            })
        else:  # POST
            data = request.get_json()
            
            # Update settings if provided
            if 'enable' in data:
                camera.on_strobe({
                    'cmd': 'enable',
                    'parameters': {'on': 1 if data['enable'] else 0}
                })
                
            if 'hold' in data:
                camera.on_strobe({
                    'cmd': 'hold',
                    'parameters': {'on': 1 if data['hold'] else 0}
                })
                
            if 'period_ns' in data or 'wait_ns' in data:
                camera.on_strobe({
                    'cmd': 'timing',
                    'parameters': {
                        'period_ns': int(data.get('period_ns', camera.strobe_data['period_ns'])),
                        'wait_ns': int(data.get('wait_ns', camera.strobe_data.get('wait_ns', 0)))
                    }
                })
            
            # Get updated settings
            camera.update_strobe_data()
            return jsonify({
                'status': 'success',
                'message': 'Strobe settings updated',
                'settings': {
                    'enabled': camera.strobe_data['enable'],
                    'hold': camera.strobe_data['hold'],
                    'period_ns': camera.strobe_data['period_ns'],
                    'wait_ns': camera.strobe_data.get('wait_ns', 0),
                    'framerate': camera.strobe_data.get('framerate', 0)
                }
            })
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/flow/sensors', methods=['GET'])
def get_flow_sensors_data():
    """Get data from all flow sensors."""
    try:
        if flow_controller is None:
            init_flow_controller()
        
        if flow_controller is None:
            return jsonify({'status': 'error', 'message': 'Flow controller is not available.'}), 503

        # The background sampler owns the SPI timing; serve its latest state.
        # Fall back to a direct update only if the sampler is not running.
        if not (flow_sampler_thread is not None and flow_sampler_thread.is_alive()):
            with flow_lock:
                flow_controller.update()

        with flow_lock:
            sensors_data = []
            for i in range(flow_controller.flow.NUM_CONTROLLERS):
                sensors_data.append({
                    "id": i,
                    "status": flow_controller.status_text[i],
                    "pressure_mbar": flow_controller.pressure_mbar_text[i],
                    "flow_ul_hr": flow_controller.flow_ul_hr_text[i],
                    "control_mode": flow_controller.control_modes_text[i],
                    "fluid_type": flow_controller.fluid_types[i]
                })
        
        return jsonify({'status': 'success', 'sensors': sensors_data})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/flow/history', methods=['GET'])
def get_flow_history():
    """Return buffered high-rate samples.

    Query params:
      since_i: sample index (int). Only samples with i > since_i are returned.
               Preferred: 'i' is strictly monotonic, 't' is not in batch mode.
      since  : epoch seconds (float). Only samples with t > since are returned (legacy).
      limit  : max samples (default 2000, newest kept).
      sensors: comma-separated ids to include (default all).
    """
    try:
        since_i = int(request.args.get('since_i', 0) or 0)
        since = float(request.args.get('since', 0) or 0)
        limit = int(request.args.get('limit', 2000) or 2000)
        sensors_arg = request.args.get('sensors')
        sel = None
        if sensors_arg:
            sel = [int(s) for s in sensors_arg.split(',') if s.strip() != '']

        snapshot = list(flow_history)          # deque -> list is atomic enough (GIL)
        if since_i > 0:
            cut = len(snapshot)
            while cut > 0 and snapshot[cut - 1]['i'] > since_i:
                cut -= 1
            snapshot = snapshot[cut:]
        elif since > 0:
            # samples are roughly time-ordered; walk from the end
            cut = len(snapshot)
            while cut > 0 and snapshot[cut - 1]['t'] > since:
                cut -= 1
            snapshot = snapshot[cut:]
        if len(snapshot) > limit:
            snapshot = snapshot[-limit:]

        if sel is not None:
            out = []
            for s in snapshot:
                o = {
                    'i': s['i'],
                    't': s['t'],
                    'flow_ul_hr': [s['flow_ul_hr'][i] for i in sel],
                    'pressure_mbar': [s['pressure_mbar'][i] for i in sel],
                    'status': [s['status'][i] for i in sel],
                    'refresh_counter': s['refresh_counter'],
                }
                for k in ('chan', 'seq', 't_pic_ms', 'flow_raw'):
                    if k in s:
                        o[k] = s[k]
                out.append(o)
            snapshot = out

        return jsonify({
            'status': 'success',
            'sensors': sel if sel is not None else list(range(flow_controller.flow.NUM_CONTROLLERS)) if flow_controller else [],
            'count': len(snapshot),
            'latest_t': snapshot[-1]['t'] if snapshot else since,
            'latest_i': snapshot[-1]['i'] if snapshot else since_i,
            'samples': snapshot,
            'sampler': flow_sampler_stats,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/flow/sampler', methods=['GET'])
def get_flow_sampler():
    """Sampler diagnostics: target vs actual rate, errors, buffer fill."""
    stats = dict(flow_sampler_stats)
    stats['buffer_len'] = len(flow_history)
    stats['buffer_max'] = flow_history.maxlen
    if len(flow_history) > 1:
        stats['buffer_seconds'] = round(flow_history[-1]['t'] - flow_history[0]['t'], 1)
    return jsonify({'status': 'success', 'sampler': stats})


# ---- Firmware v3 diagnostics / configuration --------------------------------

def _require_flow():
    if flow_controller is None:
        init_flow_controller()
    return flow_controller is not None


@app.route('/api/flow/firmware', methods=['GET'])
def get_flow_firmware():
    """Firmware version reported by the PIC (v3+). Older firmware -> version null."""
    if not _require_flow():
        return jsonify({'status': 'error', 'message': 'Flow controller is not available.'}), 503
    with flow_lock:
        ok, ver = flow_controller.flow.get_fw_version()
    return jsonify({'status': 'success', 'version': {'major': ver[0], 'minor': ver[1]} if ok else None})


@app.route('/api/flow/stats', methods=['GET'])
def get_flow_stats():
    """Per-sensor read counters since PIC boot: ok, crc_err, i2c_err, not_ready.

    Query param: sensors=1,2 (default: all four).
    """
    if not _require_flow():
        return jsonify({'status': 'error', 'message': 'Flow controller is not available.'}), 503
    sensors_arg = request.args.get('sensors')
    sel = [int(s) for s in sensors_arg.split(',') if s.strip() != ''] if sensors_arg else list(range(flow_controller.flow.NUM_CONTROLLERS))
    out = {}
    with flow_lock:
        for s in sel:
            ok, st = flow_controller.flow.get_flow_stats(s)
            out[str(s)] = st if ok else None
    return jsonify({'status': 'success', 't': time.time(), 'stats': out})


@app.route('/api/flow/resolution', methods=['GET', 'POST'])
def flow_resolution():
    """GET -> current LG16 resolution (bits). POST {"bits": 9..16} -> set on all present sensors.

    16 bit = 74 ms/measurement (default, lowest noise); 13 bit = 8.9 ms; 12 bit = 4.6 ms.
    Volatile: the PIC reverts to 16 bit on reboot.
    """
    if not _require_flow():
        return jsonify({'status': 'error', 'message': 'Flow controller is not available.'}), 503
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        try:
            bits = int(body.get('bits', request.args.get('bits')))
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'bits (9..16) required'}), 400
        if bits < 9 or bits > 16:
            return jsonify({'status': 'error', 'message': 'bits must be 9..16'}), 400
        # rc == -1 means no valid reply (lost SPI transaction, ~0.3 % of queries): retry.
        for attempt in range(3):
            with flow_lock:
                ok, rc = flow_controller.flow.set_flow_resolution(bits)
            if ok or rc != -1:
                break
        if not ok:
            return jsonify({'status': 'error', 'message': 'PIC rejected resolution change', 'rc': rc}), 502
    for attempt in range(3):
        with flow_lock:
            ok, bits_now = flow_controller.flow.get_flow_resolution()
        if ok:
            break
    return jsonify({'status': 'success', 'bits': bits_now if ok else None})

# Cleanup function
def cleanup():
    global camera
    try:
        if camera is not None:
            # Stop any ongoing recordings
            if hasattr(camera, 'recording') and camera.recording:
                camera.stop_recording()
                
            # Close camera resources
            if hasattr(camera, 'camera') and camera.camera is not None:
                camera.camera.close()
                
            # Clean up strobe
            if hasattr(camera, 'strobe_cam') and camera.strobe_cam is not None:
                camera.strobe_cam.close()
                
            camera = None
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        # Close SPI
        picommon.spi_close()
        exit_event.set()

# Register cleanup to run on exit
atexit.register(cleanup)

# Start the server
if __name__ == '__main__':
    try:
        # Initialize camera and flow controller on startup
        init_camera()
        init_flow_controller()
        
        # Start the Flask server with debug=False to prevent auto-reloader issues
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup()