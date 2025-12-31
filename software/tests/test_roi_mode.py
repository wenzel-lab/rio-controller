from config import ROI_MODE_SOFTWARE, ROI_MODE_HARDWARE
from controllers.camera import Camera, WS_EVENT_ROI


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

    def set_roi_hardware(self, roi):
        self.set_calls.append(roi)
        if not self.supports_hardware:
            raise AttributeError("no hardware roi")
        if self.succeed:
            self.hardware_roi = roi
            return True
        return False

    def get_roi_constraints(self):
        return {"width": {"min": 0, "max": 100, "increment": 1, "current": 100}}

    def get_max_resolution(self):
        return (100, 100)


def _make_controller(mode: str, camera):
    cam = Camera.__new__(Camera)
    cam.camera = camera
    cam.socketio = DummySocket()
    cam.roi = None
    cam.roi_mode_config = mode
    cam.roi_mode_active = ROI_MODE_SOFTWARE
    return cam


def test_roi_software_mode_does_not_call_hardware(monkeypatch):
    dummy = DummyCamera()
    ctrl = _make_controller(ROI_MODE_SOFTWARE, dummy)
    ctrl._handle_roi_set({"parameters": {"x": 1, "y": 2, "width": 10, "height": 12}})

    assert dummy.set_calls == []  # hardware path not taken
    assert ctrl.roi_mode_active == ROI_MODE_SOFTWARE
    assert ctrl.roi == {"x": 1, "y": 2, "width": 10, "height": 12}
    assert ctrl.socketio.events[-1] == (WS_EVENT_ROI, {"roi": ctrl.roi, "mode": ROI_MODE_SOFTWARE})


def test_roi_hardware_mode_success(monkeypatch):
    dummy = DummyCamera(supports_hardware=True, succeed=True)
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set({"parameters": {"x": 5, "y": 6, "width": 20, "height": 22}})

    assert dummy.set_calls == [(5, 6, 20, 22)]
    assert ctrl.roi_mode_active == ROI_MODE_HARDWARE
    assert ctrl.socketio.events[-1] == (WS_EVENT_ROI, {"roi": ctrl.roi, "mode": ROI_MODE_HARDWARE})


def test_roi_hardware_mode_fallback_when_backend_rejects(monkeypatch):
    dummy = DummyCamera(supports_hardware=True, succeed=False)
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set({"parameters": {"x": 1, "y": 1, "width": 2, "height": 2}})

    assert dummy.set_calls == [(1, 1, 2, 2)]
    assert ctrl.roi_mode_active == ROI_MODE_SOFTWARE  # fallback
    assert ctrl.socketio.events[-1][1]["mode"] == ROI_MODE_SOFTWARE


def test_roi_hardware_mode_backend_missing_method(monkeypatch):
    class CameraNoHardware:
        def validate_and_snap_roi(self, roi):
            return roi

        def get_roi_constraints(self):
            return {}

    dummy = CameraNoHardware()
    ctrl = _make_controller(ROI_MODE_HARDWARE, dummy)
    ctrl._handle_roi_set({"parameters": {"x": 3, "y": 4, "width": 30, "height": 40}})

    assert ctrl.roi_mode_active == ROI_MODE_SOFTWARE  # fallback
    assert ctrl.roi == {"x": 3, "y": 4, "width": 30, "height": 40}
    assert ctrl.socketio.events[-1][1]["mode"] == ROI_MODE_SOFTWARE
    assert getattr(ctrl, "_roi_hardware_unsupported_logged", False) is True
