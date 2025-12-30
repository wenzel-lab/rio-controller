# software/simulation/ — Simulation backends (no-hardware execution)

This folder provides simulated implementations that allow the Rio software to run (and be tested) without physical hardware connected. In simulation mode, drivers and camera creation automatically route into these implementations.

## How simulation is activated

Set:

```bash
export RIO_SIMULATION=true
```

This affects:

- `software/drivers/spi_handler.py`: swaps in simulated GPIO + SPI routing
- `software/drivers/camera/create_camera(...)`: returns a simulated camera backend

## What’s inside (and how it maps to real hardware)

- **`spi_simulated.py`**
  - `SimulatedGPIO`: minimal `RPi.GPIO`-compatible API
  - `SimulatedSPIHandler`: routes SPI “transfers” to simulated devices based on the currently selected port

- **`flow_simulated.py`**
  - `SimulatedFlow`: implements the same packet types as the flow firmware and returns realistic-enough pressure/flow readings

- **`heater_simulated.py`**
  - `SimulatedHeater`: implements the same packet types as the sample-holder firmware (PID status, temp readings, stir, power limit, etc.)

- **`strobe_simulated.py`**
  - `SimulatedStrobe`: implements key strobe commands (enable, timing, hold, cam-read-time, trigger mode)

- **`camera_simulated.py`**
  - `SimulatedCamera`: a `BaseCamera`-compatible implementation that generates synthetic frames and supports ROI cropping
  - it can optionally load real background/droplet templates from a `droplet_AInalysis` checkout (if found), otherwise it generates synthetic droplets

## Intended use

- **Routine tests / CI-style checks**: run in simulation mode
- **UI iteration**: run the server on a development machine without requiring the Pi or attached modules
- **Hardware validation**: disable simulation and run on the Pi with hardware connected

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change simulation routing, packet behavior, or frame generation semantics, update this document.


