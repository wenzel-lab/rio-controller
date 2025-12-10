# Simulated Flow Controller Packet Handling Fix

## Problem
The simulated flow controller's `packet_query` method wasn't being used when `PiFlow` was called in simulation mode. `PiFlow` was trying to use SPI communication even in simulation mode, which failed because the simulated SPI handler doesn't route packets to simulated devices.

## Solution
Modified `PiFlow` to detect simulation mode and use `SimulatedFlow` directly:

1. **In `PiFlow.__init__()`**: Added detection of `RIO_SIMULATION` environment variable and creation of `SimulatedFlow` instance when in simulation mode.

2. **In `PiFlow.packet_query()`**: Added check at the beginning to route to `_simulated_flow.packet_query()` if simulation mode is active, bypassing SPI communication entirely.

3. **Updated `SimulatedFlow` methods**: 
   - `get_flow_target()` now matches `PiFlow.get_flow_target()` interface (returns all channels with empty list query)
   - `get_control_modes()` now matches `PiFlow.get_control_modes()` interface (returns all channels with empty list query)

## Changes Made

### `drivers/flow.py`
- Added `_simulated_flow` instance variable
- Modified `__init__()` to create `SimulatedFlow` in simulation mode
- Modified `packet_query()` to route to simulated flow in simulation mode

### `simulation/flow_simulated.py`
- Updated `get_flow_target()` to handle empty list queries (all channels)
- Updated `get_control_modes()` to handle empty list queries (all channels)
- Methods now match the real `PiFlow` interface exactly

### `tests/test_simulation.py`
- Fixed `TestSimulatedFlow.setUp()` to pass `device_port` argument

## Results
- ✅ `PiFlow.get_flow_target()` now works in simulation mode
- ✅ `PiFlow.get_control_modes()` now works in simulation mode
- ✅ `FlowWeb.get_flow_targets()` test passes
- ✅ `FlowWeb.get_control_modes()` test passes

## Testing
```bash
export RIO_SIMULATION=true
pytest tests/test_controllers.py::TestFlowWeb::test_get_control_modes
pytest tests/test_controllers.py::TestFlowWeb::test_get_flow_targets
```

Both tests now pass successfully.

