from pathlib import Path

from config import (
    CONTROL_MODE_FIRMWARE_TO_UI,
    CONTROL_MODE_UI_TO_FIRMWARE,
    FLOW_CTRL_MODE_STR,
)
from controllers.flow_web import FlowWeb


def test_mapping_roundtrip_and_hidden_mode():
    # Firmware modes 0,1,2,3 must map, with 2 hidden to UI 0.
    assert CONTROL_MODE_FIRMWARE_TO_UI[0] == 0
    assert CONTROL_MODE_FIRMWARE_TO_UI[1] == 1
    assert CONTROL_MODE_FIRMWARE_TO_UI[2] == 0  # hidden / deprecated
    assert CONTROL_MODE_FIRMWARE_TO_UI[3] == 2

    # UI modes 0,1,2 must map back to valid firmware modes.
    assert CONTROL_MODE_UI_TO_FIRMWARE[0] == 0
    assert CONTROL_MODE_UI_TO_FIRMWARE[1] == 1
    assert CONTROL_MODE_UI_TO_FIRMWARE[2] == 3

    # Display strings are aligned to UI indices.
    assert FLOW_CTRL_MODE_STR == ["Off", "Set Pressure", "Flow Closed Loop"]


def test_no_duplicate_mapping_literals_outside_source():
    """Guardrail: prevent reintroducing local copies of the mapping."""
    forbidden_fragments = [
        "{0: 0, 1: 1, 2: 0, 3: 2}",  # firmware -> UI
        "{0: 0, 1: 1, 2: 3}",  # UI -> firmware
    ]
    base = Path(__file__).resolve().parents[1]
    targets = [
        base / "controllers" / "flow_web.py",
        base / "rio-webapp" / "controllers" / "view_model.py",
        base / "rio-webapp" / "controllers" / "flow_controller.py",
    ]
    for path in targets:
        text = path.read_text()
        for fragment in forbidden_fragments:
            assert fragment not in text, f"Mapping literal found in {path}"


def test_flowweb_ui_mapping_path(monkeypatch):
    """Ensure FlowWeb uses the canonical UI->firmware mapping when setting modes."""

    class DummyFlow:
        NUM_CONTROLLERS = 1

        def __init__(self):
            self.last_set = None

        def set_control_mode(self, indices, modes):
            self.last_set = modes[0]
            return True

    flow = DummyFlow()

    fw = FlowWeb.__new__(FlowWeb)  # bypass __init__ (hardware init)
    fw.flow = flow
    fw.control_modes = [0]
    fw.control_modes_text = [FLOW_CTRL_MODE_STR[0]]
    fw.status_text = ["Init"]
    fw.flow_ul_hr_targets = [0.0]
    fw.pressure_mbar_targets = [0.0]

    # Avoid calling hardware in get_control_modes during this test.
    monkeypatch.setattr(fw, "get_control_modes", lambda: None)

    assert fw.set_control_mode(0, 2) is True  # UI mode 2 -> firmware mode 3
    assert flow.last_set == 3
