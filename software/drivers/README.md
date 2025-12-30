## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change behavior or public interfaces, please update this document.

## Purpose

This folder contains **drivers**: low-level adapters for hardware communication (SPI/GPIO) and device-specific primitives used by the device controllers in `../controllers/`.

## What belongs here / what does not

- **Belongs here**:
  - SPI/GPIO plumbing and device selection
  - byte-level/packet-level communication with module firmware
  - camera-specific implementations behind a shared interface (see `camera/`)
- **Does not belong here**:
  - application state machines and UI semantics (belongs in `../controllers/`)
  - Flask routes/WebSocket events (belongs in `../rio-webapp/`)
  - long-running background loops that coordinate multiple devices (belongs in controllers)

## Key entry points

- `spi_handler.py`: SPI/GPIO initialization and device selection (also handles simulation mode)
- `heater.py`: low-level heater module protocol driver
- `flow.py`: low-level flow/pressure protocol driver
- `strobe.py`: strobe protocol driver
- `camera/`: camera abstraction layer and camera-type implementations

## Extension points

- **New hardware module**:
  - add a driver here that speaks the module’s firmware protocol
  - keep the public surface small and stable (device controllers can provide richer behavior)

## Testing

Run tests from `software/` (simulation mode unless on hardware):

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```


