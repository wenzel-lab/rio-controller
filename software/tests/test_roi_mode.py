from config import ROI_MODE_SOFTWARE, ROI_MODE_HARDWARE
from controllers.camera import Camera, WS_EVENT_ROI, WS_EVENT_CAM


class DummySocket:
    def __init__(self):
        self.events = []

    def emit(self, name, payload):
        self.events.append((name, payload))


class DummyCamera:
    def __init__(self, supports_hardware=True, succeed=True):
        self.supports_hardware = supports_hardware
        self.succeed = succeed
        self.hardware_roi = None
        self.validate_calls = []
        self.set_calls = []

    def validate_and_snap_roi(self, roi):
        self.validate_calls.append(roi)
        return roi

    def snap_view_roi(self, roi):
        return roi

    def set_roi_hardware(self, roi):
        self.set_calls.append(roi)
        if not self.supports_hardware:
            raise AttributeError("no hardware roi")
        if self.succeed:
            self.hardware_roi = roi
            return True
        return False

    def get_stream_size(self):
        if self.hardware_roi:
            return (self.hardware_roi[2], self.hardware_roi[3])
        return (100, 100)

    def get_roi_constraints(self):
        return {"width": {"min": 0, "max": 100, "increment": 1, "current": 100}}

    def get_max_resolution(self):
        return (100, 100)


class ScheduleCamera(DummyCamera):
    def __init__(self):
        super().__init__()
        self.scheduled = None
        self.reset_wh = None

    def schedule_roi_hardware(self, roi):
        self.scheduled = roi

    def schedule_roi_reset(self, w, h):
        self.reset_wh = (w, h)

    def get_stream_size(self):
        if self.scheduled:
            return (self.scheduled[2], self.scheduled[3])
        return (100, 100)


def _make_controller(mode: str, camera):
    cam = Camera.__new__(Camera)
    cam.camera = camera
    cam.socketio = DummySocket()
    cam.roi = None
    cam.roi_mode_config = mode
    cam.roi_mode_active = ROI_MODE_SOFTWARE
    cam.display_resolution = (100, 100)
    cam.cam_data = {"display_width": 100, "display_height": 100}
    cam._pending_roi_clear = False
    cam.update = lambda: None
    return cam


def test_roi_software_preview_does_not_emit_or_call_hardware():
    dummy = DummyCamera()
    ctrl = _make_controller(ROI_MODE_SOFTWARE, dummy)
    ctrl._handle_roi_set({"parameters": {"x": 1, "y": 2, "width": 10, "height": 12}})

    assert dummy.set_calls == []
    assert ctrl.roi_mode_active == ROI_MODE_SOFTWARE
    assert ctrl.roi == {"x": 1, "y": 2, "width": 10, "height": 12}
    assert ctrl.socketio.events == []


def test_roi_hardware_mode_sync_success():
    dummy = DummyCamera(supports_hardware=True, succeed=True)
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set(
        {"parameters": {"x": 5, "y": 6, "width": 20, "height": 22, "apply_hardware": True}}
    )

    assert dummy.set_calls == [(5, 6, 20, 22)]
    assert ctrl.roi_mode_active == ROI_MODE_HARDWARE
    roi_events = [e for e in ctrl.socketio.events if e[0] == WS_EVENT_ROI]
    assert roi_events[-1][1]["hardware_applied"] is True
    assert roi_events[-1][1]["stream_width"] == 20


def test_roi_hardware_mode_deferred_schedule():
    dummy = ScheduleCamera()
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set(
        {"parameters": {"x": 5, "y": 6, "width": 20, "height": 22, "apply_hardware": True}}
    )

    assert dummy.scheduled == (5, 6, 20, 22)
    assert dummy.set_calls == []
    evt = ctrl.socketio.events[-1]
    assert evt[1]["roi_scheduled"] is True
    assert evt[1]["hardware_applied"] is False
    assert evt[1]["snapped_roi"]["width"] == 20

    ctrl._on_hardware_roi_applied(True, "crop")
    roi_events = [e for e in ctrl.socketio.events if e[0] == WS_EVENT_ROI]
    assert roi_events[-1][1]["hardware_applied"] is True
    assert any(e[0] == WS_EVENT_CAM for e in ctrl.socketio.events)


def test_roi_hardware_mode_fallback_when_backend_rejects():
    dummy = DummyCamera(supports_hardware=True, succeed=False)
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set(
        {"parameters": {"x": 1, "y": 1, "width": 2, "height": 2, "apply_hardware": True}}
    )

    assert dummy.set_calls == [(1, 1, 2, 2)]
    assert ctrl.roi_mode_active == ROI_MODE_SOFTWARE
    assert ctrl.socketio.events[-1][1]["mode"] == ROI_MODE_SOFTWARE


def test_roi_hardware_apply_failure_emits_failed():
    dummy = ScheduleCamera()
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set(
        {"parameters": {"x": 1, "y": 1, "width": 20, "height": 20, "apply_hardware": True}}
    )
    ctrl._on_hardware_roi_applied(False, "crop")
    assert ctrl.socketio.events[-1] == (WS_EVENT_ROI, {"roi_apply_failed": True})


def test_roi_clear_deferred_reset():
    dummy = ScheduleCamera()
    dummy.get_max_resolution = lambda: (1440, 1080)
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._sync_default_stream_resolution = lambda: (1440, 1080)
    ctrl._handle_roi_clear()

    assert dummy.reset_wh == (1440, 1080)
    assert ctrl._pending_roi_clear is True
    assert not any(e[1].get("cleared") for e in ctrl.socketio.events)

    ctrl._on_hardware_roi_applied(True, "reset")
    cleared_events = [e for e in ctrl.socketio.events if e[0] == WS_EVENT_ROI and e[1].get("cleared")]
    assert cleared_events
    assert cleared_events[-1][1]["stream_width"] == 100


def test_roi_hardware_mode_backend_missing_method():
    class CameraNoHardware:
        def validate_and_snap_roi(self, roi):
            return roi

        def snap_view_roi(self, roi):
            return roi

        def get_roi_constraints(self):
            return {}

    dummy = CameraNoHardware()
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set(
        {"parameters": {"x": 3, "y": 4, "width": 30, "height": 40, "apply_hardware": True}}
    )

    assert ctrl.roi_mode_active == ROI_MODE_SOFTWARE
    assert ctrl.roi == {"x": 3, "y": 4, "width": 30, "height": 40}
    assert ctrl.socketio.events[-1][1]["mode"] == ROI_MODE_SOFTWARE
    assert getattr(ctrl, "_roi_hardware_unsupported_logged", False) is True
