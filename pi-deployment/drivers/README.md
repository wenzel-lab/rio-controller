# software/drivers/ — Hardware drivers (SPI/GPIO + camera backends)

This folder contains the lowest-level adapters that talk to Rio hardware: SPI/GPIO selection, packet framing, and per-module protocol drivers. Controllers in `../controllers/` build “application behaviors” on top of these primitives.

## What belongs here / what does not

- **Belongs here**: device protocol constants, packet framing, and “one module ↔ one firmware protocol” drivers.
- **Does not belong here**: UI semantics and long-running orchestration loops (those belong in `../controllers/`), and HTTP/WebSocket handling (belongs in `../rio-webapp/`).

## SPI/GPIO substrate (`spi_handler.py`)

`spi_handler.py` is the shared substrate used by SPI-speaking drivers:

- **Simulation switch**: `RIO_SIMULATION=true` swaps in simulated GPIO/SPI from `../simulation/spi_simulated.py`.
- **SPI lifecycle**:
  - `spi_init(bus, mode, speed_hz)` initializes the global `spi_handler.spi`
  - drivers expect `spi_handler.spi` to be initialized before calling into them
- **Chip select**: the board uses GPIO “ports” (see `PORT_*` constants) and `spi_select_device(port)` to select a module.
- **Concurrency**: `spi_lock()` / `spi_release()` serialize access across modules.

## Packet framing (common pattern)

Multiple drivers follow the same PIC packet framing:

- `STX = 2`
- message: `[STX][size][packet_type][data...][checksum]`
- checksum is chosen so that the sum of all bytes modulo 256 equals 0

See: `drivers/flow.py`, `drivers/heater.py`, `drivers/strobe.py` (and the corresponding firmware folders under `hardware-modules/*/*_pic/`).

## Module drivers (public surfaces)

- **Flow/pressure**: `flow.py` → `class PiFlow`
  - packet types align with `hardware-modules/pressure-flow-control/pressure_and_flow_pic/`
  - typical calls: `get_id()`, `set_pressure(...)`, `get_pressure_actual()`, `set_flow(...)`, `get_control_modes()`, `set_control_mode(...)`, PID constant get/set
  - **simulation**: may delegate to `simulation.flow_simulated.SimulatedFlow` when enabled

- **Heater/stirrer**: `heater.py` → `class PiHolder`
  - packet types align with `hardware-modules/heating-stirring/sample_holder_pic/`
  - typical calls: `get_id()`, `set_pid_temp(...)`, `get_temp_actual()`, PID get/set, autotune, stir get/set, power-limit get/set

- **Strobe**: `strobe.py` → `class PiStrobe`
  - packet types align with `hardware-modules/strobe-imaging/strobe_pic/`
  - typical calls: `set_enable(...)`, `set_timing(wait_ns, period_ns)`, `set_hold(...)`, `get_cam_read_time()`, `set_trigger_mode(hardware_trigger)`

- **Camera**: `camera/` subpackage (see `camera/README.md`)
  - abstraction layer and backends (Pi camera + Mako)

## Testing

Prefer running tests in simulation mode:

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change protocols, packet framing, or driver public methods, update this document.


