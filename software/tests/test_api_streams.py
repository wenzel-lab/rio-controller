from pathlib import Path

from api.streams import Aggregator


class DummyFlow:
    NUM_CONTROLLERS = 2

    def __init__(self):
        self.pressure_mbar_targets = [10.0, 20.0]
        self.flow_ul_hr_targets = [100.0, 200.0]
        self.control_modes = [0, 1]

        class FlowLow:
            NUM_CONTROLLERS = 2

            @staticmethod
            def get_pressure_actual(idx):
                return True, 5.0 * (idx + 1)

            @staticmethod
            def get_flow_actual(idx):
                return True, 50.0 * (idx + 1)

        self.flow = FlowLow()

    def get_pressure_targets(self):
        return True

    def get_flow_targets(self):
        return True

    def get_control_modes(self):
        return True


class DummyHeater:
    def __init__(self, temp):
        self.temp_c_actual = temp
        self.temp_c_target = temp
        self.pid_enabled = False
        self.stir_enabled = False
        self.autotuning = False
        self.status_text = "Idle"

    def update(self):
        pass


def test_aggregator_flow_calibration_applied():
    channel_config = {
        "flow": {
            "0": {
                "enabled": True,
                "name": "oil",
                "liquid_type": "mineral_oil",
                "calibration_factor": 2.0,
            },
            "1": {
                "enabled": True,
                "name": "cells",
                "liquid_type": "aqueous",
                "calibration_factor": 1.0,
            },
        },
        "pressure": {},
        "heater": {},
    }
    agg = Aggregator(flow=DummyFlow(), heaters=None, channel_config=channel_config)
    payload = async_lambda(agg._sample_flow("now", [0, 1]))
    assert payload is not None
    samples = payload["samples"][0]
    assert samples["pressure_actuals_mbar"] == [10.0, 10.0]
    assert samples["flow_actuals_ul_hr"] == [100.0, 100.0]


def test_aggregator_capture_writes_csv(tmp_path: Path):
    agg = Aggregator(flow=None, heaters=None, channel_config={})
    out = tmp_path / "capture.csv"
    agg.start_capture(topics=["flow"], channels={}, path=str(out))
    agg._maybe_capture("flow", {"test": True})
    agg.stop_capture()
    data = out.read_text().splitlines()
    assert len(data) >= 2
    assert "flow" in data[1]


# Helper to run async functions in pytest without adding heavy fixtures
def async_lambda(coro):
    import asyncio

    return asyncio.run(coro)
