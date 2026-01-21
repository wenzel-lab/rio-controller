"""Unit tests for LabThings Thing classes."""

import pytest
from unittest.mock import MagicMock
from typing import List

from labthings_fastapi.exceptions import InvocationError

from api.things.flow_thing import FlowThing
from api.things.heater_thing import HeaterThing
from api.things.camera_thing import CameraThing
from api.things.droplet_thing import DropletThing
from api.things.pump_thing import PumpThing
from api.schemas import FlowState, HeaterState
from labthings_fastapi.outputs.blob import Blob


# ============================================================================
# Mock Controllers
# ============================================================================


class MockFlow:
    """Mock flow controller for testing."""

    NUM_CONTROLLERS = 4

    def __init__(self):
        self.pressure_mbar_targets = [0.0, 0.0, 0.0, 0.0]
        self.flow_ul_hr_targets = [0.0, 0.0, 0.0, 0.0]
        self.control_modes = [0, 0, 0, 0]
        self.control_modes_text = ["Off", "Off", "Off", "Off"]

    def get_pressure_actual(self):
        """Return (ok, [pressures])."""
        return True, [10.0, 20.0, 30.0, 40.0]

    def get_flow_actual(self):
        """Return (ok, [flows])."""
        return True, [100.0, 200.0, 300.0, 400.0]


class MockFlowWeb:
    """Mock FlowWeb controller for testing."""

    def __init__(self):
        self.flow = MockFlow()
        self.pressure_mbar_targets = [0.0, 0.0, 0.0, 0.0]
        self.flow_ul_hr_targets = [0.0, 0.0, 0.0, 0.0]
        self.control_modes = [0, 0, 0, 0]
        self.control_modes_text = ["Off", "Off", "Off", "Off"]

    def get_pressure_targets(self):
        """Update pressure targets."""
        return True

    def get_flow_targets(self):
        """Update flow targets."""
        return True

    def get_control_modes(self):
        """Update control modes."""
        return True

    def set_pressure(self, index: int, pressure_mbar: float) -> bool:
        """Set pressure target."""
        if not (0 <= index <= 3):
            return False
        self.pressure_mbar_targets[index] = pressure_mbar
        return True

    def set_flow(self, index: int, flow_ul_hr: float) -> bool:
        """Set flow target."""
        if not (0 <= index <= 3):
            return False
        self.flow_ul_hr_targets[index] = flow_ul_hr
        return True

    def set_control_mode(self, index: int, mode: int) -> bool:
        """Set control mode."""
        if not (0 <= index <= 3):
            return False
        self.control_modes[index] = mode
        mode_names = {0: "Off", 1: "Set Pressure", 2: "Flow Closed Loop"}
        self.control_modes_text[index] = mode_names.get(mode, "Off")
        return True

    def set_flow_pi_consts(self, index: int, consts: List[int]) -> bool:
        """Set PI constants."""
        if not (0 <= index <= 3):
            return False
        return True


class MockHeaterWeb:
    """Mock heater_web controller for testing."""

    def __init__(self, temp_actual=25.0, temp_target=25.0, pid_enabled=False, stir_enabled=False):
        self.temp_c_actual = temp_actual
        self.temp_c_target = temp_target
        self.pid_enabled = pid_enabled
        self.stir_enabled = stir_enabled
        self.autotuning = False
        self.status_text = "Idle"

    def update(self):
        """Update heater state."""
        pass

    def set_temp(self, temp_c: float):
        """Set target temperature."""
        self.temp_c_target = temp_c

    def set_pid_running(self, enabled: int):
        """Enable/disable PID."""
        self.pid_enabled = bool(enabled)

    def set_stir_running(self, enabled: int):
        """Enable/disable stirrer."""
        self.stir_enabled = bool(enabled)


class MockCamera:
    """Mock Camera controller for testing."""

    def __init__(self, has_frame=True):
        self._has_frame = has_frame
        self._frame = b"fake_jpeg_data" if has_frame else None
        self.thread = None

    def initialize(self):
        """Initialize camera."""
        self.thread = MagicMock()
        self.thread.is_alive = lambda: True

    def get_frame(self) -> bytes | None:
        """Get camera frame."""
        return self._frame

    def on_cam(self, msg: dict):
        """Handle camera command."""
        pass

    def on_roi(self, msg: dict):
        """Handle ROI command."""
        pass

    def on_strobe(self, msg: dict):
        """Handle strobe command."""
        pass


class MockDropletController:
    """Mock DropletDetectorController for testing."""

    def __init__(self, running=False):
        self.running = running
        self.frame_count = 0
        self.droplet_count_total = 0
        self.processing_rate_hz = 30.0

    def get_statistics(self) -> dict:
        """Get statistics."""
        return {
            "mean_size": 10.0,
            "std_size": 2.0,
            "min_size": 5.0,
            "max_size": 15.0,
            "count": self.droplet_count_total,
        }

    def get_histogram(self) -> dict:
        """Get histogram."""
        return {
            "bins": [0, 5, 10, 15, 20],
            "counts": [0, 5, 10, 3, 0],
        }

    def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return {
            "fps": self.processing_rate_hz,
            "cpu_percent": 10.0,
            "memory_mb": 50.0,
        }

    def start(self) -> bool:
        """Start detection."""
        if self.running:
            return False
        self.running = True
        return True

    def stop(self):
        """Stop detection."""
        self.running = False


# ============================================================================
# Pump Mock
# ============================================================================


class MockPumpController:
    """Mock pump controller for testing."""

    def __init__(self):
        self.states = {
            "A": {"pump": "A", "flow": 100.0, "diameter": 8.17, "direction": 1, "state": False},
            "B": {"pump": "B", "flow": 200.0, "diameter": 8.17, "direction": -1, "state": True},
            "C": {"pump": "C", "flow": 0.0, "diameter": 8.17, "direction": 1, "state": False},
            "D": {"pump": "D", "flow": 0.0, "diameter": 8.17, "direction": 1, "state": False},
        }

    def get_state(self, pump: str):
        return self.states[pump]

    def get_all_states(self):
        return self.states

    def set_flow(self, pump: str, flow: float) -> bool:
        self.states[pump]["flow"] = flow
        return True

    def set_diameter(self, pump: str, diameter: float) -> bool:
        self.states[pump]["diameter"] = diameter
        return True

    def set_direction(self, pump: str, direction: int) -> bool:
        self.states[pump]["direction"] = direction
        return True

    def set_state(self, pump: str, state: bool) -> bool:
        self.states[pump]["state"] = state
        return True

    def set_unit(self, pump: str, unit: str) -> bool:
        self.states[pump]["unit"] = unit
        return True

    def set_gearbox(self, pump: str, gearbox: str) -> bool:
        self.states[pump]["gearbox"] = gearbox
        return True

    def set_microstep(self, pump: str, microstep: str) -> bool:
        self.states[pump]["microstep"] = microstep
        return True

    def set_threadrod(self, pump: str, threadrod: str) -> bool:
        self.states[pump]["threadrod"] = threadrod
        return True

    def set_enable(self, pump: str, enabled: bool) -> bool:
        self.states[pump]["enabled"] = enabled
        return True


# ============================================================================
# FlowThing Tests
# ============================================================================


class TestFlowThing:
    """Tests for FlowThing."""

    def test_flow_thing_state_property(self):
        """Test FlowThing.state property returns correct FlowState."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        state = thing.state

        assert isinstance(state, FlowState)
        assert len(state.pressure_targets_mbar) == 4
        assert len(state.pressure_actuals_mbar) == 4
        assert len(state.flow_targets_ul_hr) == 4
        assert len(state.flow_actuals_ul_hr) == 4
        assert state.pressure_actuals_mbar == [10.0, 20.0, 30.0, 40.0]
        assert state.flow_actuals_ul_hr == [100.0, 200.0, 300.0, 400.0]

    def test_flow_thing_state_property_missing_controller(self):
        """Test FlowThing.state raises RuntimeError when controller is None."""
        thing = FlowThing(None)

        with pytest.raises(RuntimeError, match="Flow controller unavailable"):
            _ = thing.state

    def test_flow_thing_state_property_invalid_pressure_response(self):
        """Test FlowThing.state handles invalid pressure response."""
        mock_flow = MockFlowWeb()
        mock_flow.flow.get_pressure_actual = lambda: (False, [0.0, 0.0, 0.0, 0.0])
        thing = FlowThing(mock_flow)

        state = thing.state

        assert state.pressure_actuals_mbar == [0.0, 0.0, 0.0, 0.0]

    def test_flow_thing_state_property_invalid_flow_response(self):
        """Test FlowThing.state handles invalid flow response."""
        mock_flow = MockFlowWeb()
        mock_flow.flow.get_flow_actual = lambda: (False, [0.0, 0.0, 0.0, 0.0])
        thing = FlowThing(mock_flow)

        state = thing.state

        assert state.flow_actuals_ul_hr == [0.0, 0.0, 0.0, 0.0]

    def test_flow_thing_set_pressure_action_valid(self):
        """Test FlowThing.set_pressure with valid parameters."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        result = thing.set_pressure(index=0, pressure_mbar=50.0)

        assert result == {"ok": True}
        assert mock_flow.pressure_mbar_targets[0] == 50.0

    def test_flow_thing_set_pressure_action_invalid_index_low(self):
        """Test FlowThing.set_pressure raises InvocationError for index < 0."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="Invalid channel index"):
            thing.set_pressure(index=-1, pressure_mbar=50.0)

    def test_flow_thing_set_pressure_action_invalid_index_high(self):
        """Test FlowThing.set_pressure raises InvocationError for index > 3."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="Invalid channel index"):
            thing.set_pressure(index=4, pressure_mbar=50.0)

    def test_flow_thing_set_pressure_action_unavailable_controller(self):
        """Test FlowThing.set_pressure raises InvocationError when controller is None."""
        thing = FlowThing(None)

        with pytest.raises(InvocationError, match="Flow controller unavailable"):
            thing.set_pressure(index=0, pressure_mbar=50.0)

    def test_flow_thing_set_pressure_action_controller_returns_false(self):
        """Test FlowThing.set_pressure raises InvocationError when controller returns False."""
        mock_flow = MockFlowWeb()
        mock_flow.set_pressure = lambda idx, val: False
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="Failed to set pressure"):
            thing.set_pressure(index=0, pressure_mbar=50.0)

    def test_flow_thing_set_flow_action_valid(self):
        """Test FlowThing.set_flow with valid parameters."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        result = thing.set_flow(index=1, flow_ul_hr=150.0)

        assert result == {"ok": True}
        assert mock_flow.flow_ul_hr_targets[1] == 150.0

    def test_flow_thing_set_flow_action_invalid_index(self):
        """Test FlowThing.set_flow raises InvocationError for invalid index."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="Invalid channel index"):
            thing.set_flow(index=5, flow_ul_hr=150.0)

    def test_flow_thing_set_mode_action_valid(self):
        """Test FlowThing.set_mode with valid UI mode."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        # Import mode mapping to verify correct mapping
        from config import CONTROL_MODE_UI_TO_FIRMWARE

        result = thing.set_mode(index=0, mode_ui=1)

        assert result == {"ok": True}
        # Mode 1 (Set Pressure) should map to firmware mode from CONTROL_MODE_UI_TO_FIRMWARE
        expected_firmware_mode = CONTROL_MODE_UI_TO_FIRMWARE.get(1, 0)
        assert mock_flow.control_modes[0] == expected_firmware_mode

    def test_flow_thing_set_mode_action_invalid_mode(self):
        """Test FlowThing.set_mode with invalid mode (falls back to mode 0)."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        # Invalid mode should map to 0 (Off)
        result = thing.set_mode(index=0, mode_ui=999)

        assert result == {"ok": True}
        assert mock_flow.control_modes[0] == 0

    def test_flow_thing_set_pi_consts_action_valid(self):
        """Test FlowThing.set_pi_consts with valid values."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        result = thing.set_pi_consts(index=0, p=10, i=5)

        assert result == {"ok": True}

    def test_flow_thing_set_pi_consts_action_negative_p(self):
        """Test FlowThing.set_pi_consts raises InvocationError for negative P."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="PI constants must be non-negative"):
            thing.set_pi_consts(index=0, p=-1, i=5)

    def test_flow_thing_set_pi_consts_action_negative_i(self):
        """Test FlowThing.set_pi_consts raises InvocationError for negative I."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="PI constants must be non-negative"):
            thing.set_pi_consts(index=0, p=10, i=-1)

    def test_flow_thing_set_pi_consts_action_controller_failure(self):
        """Test FlowThing.set_pi_consts raises InvocationError when controller returns False."""
        mock_flow = MockFlowWeb()
        mock_flow.set_flow_pi_consts = lambda idx, consts: False
        thing = FlowThing(mock_flow)

        with pytest.raises(InvocationError, match="Failed to set PI constants"):
            thing.set_pi_consts(index=0, p=10, i=5)


# ============================================================================
# HeaterThing Tests
# ============================================================================


class TestHeaterThing:
    """Tests for HeaterThing."""

    def test_heater_thing_state_property(self):
        """Test HeaterThing.state property returns correct HeaterState."""
        heaters = [
            MockHeaterWeb(temp_actual=25.0, temp_target=30.0, pid_enabled=True),
            MockHeaterWeb(temp_actual=37.0, temp_target=37.0, pid_enabled=False),
            MockHeaterWeb(temp_actual=20.0, temp_target=20.0, stir_enabled=True),
            MockHeaterWeb(temp_actual=50.0, temp_target=50.0),
        ]
        thing = HeaterThing(heaters)

        state = thing.state

        assert isinstance(state, HeaterState)
        assert len(state.heaters) == 4
        assert state.heaters[0].temp_c_actual == 25.0
        assert state.heaters[0].temp_c_target == 30.0
        assert state.heaters[0].pid_enabled is True
        assert state.heaters[1].temp_c_actual == 37.0
        assert state.heaters[2].stir_enabled is True

    def test_heater_thing_state_property_missing_heaters(self):
        """Test HeaterThing.state raises RuntimeError when heaters is None."""
        thing = HeaterThing(None)

        with pytest.raises(RuntimeError, match="Heaters unavailable"):
            _ = thing.state

    def test_heater_thing_set_temp_action_valid(self):
        """Test HeaterThing.set_temp with valid parameters."""
        heaters = [MockHeaterWeb() for _ in range(4)]
        thing = HeaterThing(heaters)

        result = thing.set_temp(index=0, temp_c=37.0)

        assert result == {"ok": True}
        assert heaters[0].temp_c_target == 37.0

    def test_heater_thing_set_temp_action_invalid_index_low(self):
        """Test HeaterThing.set_temp raises InvocationError for index < 0."""
        heaters = [MockHeaterWeb() for _ in range(4)]
        thing = HeaterThing(heaters)

        with pytest.raises(InvocationError, match="Invalid heater index"):
            thing.set_temp(index=-1, temp_c=37.0)

    def test_heater_thing_set_temp_action_invalid_index_high(self):
        """Test HeaterThing.set_temp raises InvocationError for index >= len(heaters)."""
        heaters = [MockHeaterWeb() for _ in range(4)]
        thing = HeaterThing(heaters)

        with pytest.raises(InvocationError, match="Invalid heater index"):
            thing.set_temp(index=4, temp_c=37.0)

    def test_heater_thing_set_pid_action_enable(self):
        """Test HeaterThing.set_pid enables PID."""
        heaters = [MockHeaterWeb() for _ in range(4)]
        thing = HeaterThing(heaters)

        result = thing.set_pid(index=0, enabled=True)

        assert result == {"ok": True}
        assert heaters[0].pid_enabled is True

    def test_heater_thing_set_pid_action_disable(self):
        """Test HeaterThing.set_pid disables PID."""
        heaters = [MockHeaterWeb(pid_enabled=True) for _ in range(4)]
        thing = HeaterThing(heaters)

        result = thing.set_pid(index=0, enabled=False)

        assert result == {"ok": True}
        assert heaters[0].pid_enabled is False

    def test_heater_thing_set_stir_action_enable(self):
        """Test HeaterThing.set_stir enables stirrer."""
        heaters = [MockHeaterWeb() for _ in range(4)]
        thing = HeaterThing(heaters)

        result = thing.set_stir(index=0, enabled=True)

        assert result == {"ok": True}
        assert heaters[0].stir_enabled is True

    def test_heater_thing_set_stir_action_disable(self):
        """Test HeaterThing.set_stir disables stirrer."""
        heaters = [MockHeaterWeb(stir_enabled=True) for _ in range(4)]
        thing = HeaterThing(heaters)

        result = thing.set_stir(index=0, enabled=False)

        assert result == {"ok": True}
        assert heaters[0].stir_enabled is False


# ============================================================================
# CameraThing Tests
# ============================================================================


class TestCameraThing:
    """Tests for CameraThing."""

    def test_camera_thing_snapshot_action_valid(self):
        """Test CameraThing.snapshot returns Blob with JPEG data."""
        mock_camera = MockCamera(has_frame=True)
        mock_camera.thread = MagicMock()
        mock_camera.thread.is_alive = lambda: True
        thing = CameraThing(mock_camera)

        blob = thing.snapshot()

        assert isinstance(blob, Blob)
        assert blob.content == b"fake_jpeg_data"
        assert blob.media_type == "image/jpeg"

    def test_camera_thing_snapshot_action_initializes_if_thread_dead(self):
        """Test CameraThing.snapshot initializes camera if thread is not alive."""
        mock_camera = MockCamera(has_frame=True)
        mock_camera.thread = None
        thing = CameraThing(mock_camera)

        blob = thing.snapshot()

        assert isinstance(blob, Blob)
        assert mock_camera.thread is not None

    def test_camera_thing_snapshot_action_no_frame(self):
        """Test CameraThing.snapshot raises InvocationError when no frame available."""
        mock_camera = MockCamera(has_frame=False)
        mock_camera.thread = MagicMock()
        mock_camera.thread.is_alive = lambda: True
        thing = CameraThing(mock_camera)

        with pytest.raises(InvocationError, match="No frame available"):
            thing.snapshot()

    def test_camera_thing_snapshot_action_unavailable(self):
        """Test CameraThing.snapshot raises InvocationError when camera is None."""
        thing = CameraThing(None)

        with pytest.raises(InvocationError, match="Camera unavailable"):
            thing.snapshot()

    def test_camera_thing_set_resolution_action_with_preset(self):
        """Test CameraThing.set_resolution with preset."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.set_resolution(preset="hd")

        assert result == {"ok": True}

    def test_camera_thing_set_resolution_action_with_width_height(self):
        """Test CameraThing.set_resolution with width/height."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.set_resolution(width=1920, height=1080)

        assert result == {"ok": True}

    def test_camera_thing_set_roi_action_valid(self):
        """Test CameraThing.set_roi with valid coordinates."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.set_roi(x=100, y=100, w=200, h=200)

        assert result == {"ok": True}

    def test_camera_thing_clear_roi_action(self):
        """Test CameraThing.clear_roi."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.clear_roi()

        assert result == {"ok": True}

    def test_camera_thing_strobe_enable_action(self):
        """Test CameraThing.strobe_enable."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.strobe_enable(on=True)

        assert result == {"ok": True}

    def test_camera_thing_strobe_hold_action(self):
        """Test CameraThing.strobe_hold."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.strobe_hold(on=True)

        assert result == {"ok": True}

    def test_camera_thing_strobe_timing_action_with_wait(self):
        """Test CameraThing.strobe_timing with wait_ns."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.strobe_timing(period_ns=1000000, wait_ns=500000)

        assert result == {"ok": True}

    def test_camera_thing_strobe_timing_action_without_wait(self):
        """Test CameraThing.strobe_timing without wait_ns."""
        mock_camera = MockCamera()
        thing = CameraThing(mock_camera)

        result = thing.strobe_timing(period_ns=1000000, wait_ns=None)

        assert result == {"ok": True}


# ============================================================================
# DropletThing Tests
# ============================================================================


class TestDropletThing:
    """Tests for DropletThing."""

    def test_droplet_thing_status_property(self):
        """Test DropletThing.status property."""
        mock_controller = MockDropletController(running=True)
        mock_controller.frame_count = 100
        mock_controller.droplet_count_total = 50
        mock_controller.processing_rate_hz = 30.0
        thing = DropletThing(mock_controller)

        status = thing.status

        assert isinstance(status, dict)
        assert status["running"] is True
        assert status["frame_count"] == 100
        assert status["droplet_count_total"] == 50
        assert status["processing_rate_hz"] == 30.0

    def test_droplet_thing_status_property_unavailable(self):
        """Test DropletThing.status raises RuntimeError when controller is None."""
        thing = DropletThing(None)

        with pytest.raises(RuntimeError, match="Droplet controller unavailable"):
            _ = thing.status

    def test_droplet_thing_statistics_property(self):
        """Test DropletThing.statistics property."""
        mock_controller = MockDropletController()
        thing = DropletThing(mock_controller)

        stats = thing.statistics

        assert isinstance(stats, dict)
        assert "mean_size" in stats
        assert "std_size" in stats
        assert stats["count"] == 0

    def test_droplet_thing_histogram_property(self):
        """Test DropletThing.histogram property."""
        mock_controller = MockDropletController()
        thing = DropletThing(mock_controller)

        histogram = thing.histogram

        assert isinstance(histogram, dict)
        assert "bins" in histogram
        assert "counts" in histogram

    def test_droplet_thing_performance_property(self):
        """Test DropletThing.performance property."""
        mock_controller = MockDropletController()
        thing = DropletThing(mock_controller)

        performance = thing.performance

        assert isinstance(performance, dict)
        assert "fps" in performance
        assert "cpu_percent" in performance

    def test_droplet_thing_start_action_success(self):
        """Test DropletThing.start successfully starts detection."""
        mock_controller = MockDropletController(running=False)
        thing = DropletThing(mock_controller)

        result = thing.start()

        assert result == {"ok": True}
        assert mock_controller.running is True

    def test_droplet_thing_start_action_failure(self):
        """Test DropletThing.start raises InvocationError when start fails."""
        mock_controller = MockDropletController(running=True)
        thing = DropletThing(mock_controller)

        with pytest.raises(InvocationError, match="Failed to start droplet detection"):
            thing.start()

    def test_droplet_thing_start_action_unavailable(self):
        """Test DropletThing.start raises InvocationError when controller is None."""
        thing = DropletThing(None)

        with pytest.raises(InvocationError, match="Droplet controller unavailable"):
            thing.start()

    def test_droplet_thing_stop_action(self):
        """Test DropletThing.stop."""
        mock_controller = MockDropletController(running=True)
        thing = DropletThing(mock_controller)

        result = thing.stop()

        assert result == {"ok": True}
        assert mock_controller.running is False

    def test_droplet_thing_stop_action_unavailable(self):
        """Test DropletThing.stop raises InvocationError when controller is None."""
        thing = DropletThing(None)

        with pytest.raises(InvocationError, match="Droplet controller unavailable"):
            thing.stop()


# ============================================================================
# PumpThing Tests
# ============================================================================


class TestPumpThing:
    """Tests for PumpThing."""

    def test_pump_thing_state_property(self):
        mock_controller = MockPumpController()
        thing = PumpThing(mock_controller)

        state = thing.state

        assert "pumps" in state
        assert "A" in state["pumps"]

    def test_pump_thing_state_property_unavailable(self):
        thing = PumpThing(None)

        with pytest.raises(RuntimeError, match="Pump controller unavailable"):
            _ = thing.state

    def test_pump_thing_set_flow_action(self):
        mock_controller = MockPumpController()
        thing = PumpThing(mock_controller)

        result = thing.set_flow(pump="A", flow=10.0)

        assert result == {"ok": True}
        assert mock_controller.states["A"]["flow"] == 10.0

    def test_pump_thing_set_flow_action_unavailable(self):
        thing = PumpThing(None)

        with pytest.raises(InvocationError, match="Pump controller unavailable"):
            thing.set_flow(pump="A", flow=10.0)

    def test_pump_thing_set_diameter_action(self):
        mock_controller = MockPumpController()
        thing = PumpThing(mock_controller)

        result = thing.set_diameter(pump="A", diameter=10.0)

        assert result == {"ok": True}
        assert mock_controller.states["A"]["diameter"] == 10.0

    def test_pump_thing_set_direction_action(self):
        mock_controller = MockPumpController()
        thing = PumpThing(mock_controller)

        result = thing.set_direction(pump="A", direction=1)

        assert result == {"ok": True}
        assert mock_controller.states["A"]["direction"] == 1

    def test_pump_thing_set_state_action(self):
        mock_controller = MockPumpController()
        thing = PumpThing(mock_controller)

        result = thing.set_state(pump="A", state=True)

        assert result == {"ok": True}
        assert mock_controller.states["A"]["state"] is True


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestThingEdgeCases:
    """Edge case tests for Things."""

    def test_flow_thing_boundary_values(self):
        """Test FlowThing with boundary values (index 0 and 3)."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        # Test index 0
        result = thing.set_pressure(index=0, pressure_mbar=0.0)
        assert result == {"ok": True}

        # Test index 3
        result = thing.set_pressure(index=3, pressure_mbar=10000.0)
        assert result == {"ok": True}

    def test_heater_thing_empty_list(self):
        """Test HeaterThing with empty heaters list."""
        thing = HeaterThing([])

        with pytest.raises(InvocationError, match="Invalid heater index"):
            thing.set_temp(index=0, temp_c=37.0)

    def test_flow_thing_large_values(self):
        """Test FlowThing with large pressure/flow values."""
        mock_flow = MockFlowWeb()
        thing = FlowThing(mock_flow)

        # Large pressure
        result = thing.set_pressure(index=0, pressure_mbar=100000.0)
        assert result == {"ok": True}

        # Large flow
        result = thing.set_flow(index=0, flow_ul_hr=1000000.0)
        assert result == {"ok": True}
