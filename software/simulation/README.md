## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change simulation behavior or public interfaces, please update this document.

## Purpose

This folder contains **simulation implementations** used to run the Rio software without physical hardware. Simulation mode is intended for development, CI-style testing, and UI iteration.

## What belongs here / what does not

- **Belongs here**:
  - simulated SPI/GPIO, camera frames, and device behaviors that mimic driver interfaces
  - deterministic behavior suitable for tests
- **Does not belong here**:
  - real hardware access (belongs in `../drivers/`)
  - UI formatting or Flask routes (belongs in `../rio-webapp/`)

## How simulation is activated

Simulation is activated via the environment variable:

```bash
export RIO_SIMULATION=true
```

Many tests set this automatically; prefer running tests from `software/`.

## Key files

- `camera_simulated.py`: simulated camera frame generation + ROI cropping support
- `spi_simulated.py`: simulated SPI handler backend
- `flow_simulated.py`, `heater_simulated.py`, `strobe_simulated.py`: simulated module behaviors


