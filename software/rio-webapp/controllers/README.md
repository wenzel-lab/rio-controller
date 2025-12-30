## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change event names or payload formats, please update this document.

## Purpose

This folder contains **web controllers**: handlers for HTTP/WebSocket events that translate UI requests into calls on the device controllers in `../../controllers/`.

## What belongs here / what does not

- **Belongs here**:
  - WebSocket event handlers and payload parsing
  - mapping from UI intent (buttons/inputs) to device controller calls
  - emitting view-friendly updates back to the UI
- **Does not belong here**:
  - low-level hardware comms (belongs in `../../drivers/`)
  - complex device state machines or protocol mappings duplicated across layers (prefer central mappings in `../../config.py` and device controllers)

## Key files

- `camera_controller.py`: camera selection and camera-type switching
- `flow_controller.py`: flow/pressure commands from UI to device controller
- `heater_controller.py`: heater/stirring commands from UI to device controller
- `droplet_web_controller.py`: droplet detection UI events and broadcast updates
- `view_model.py`: formatting helper for template/client payloads (presentation shaping only)

## WebSocket contract guidance (high level)

Event names and payload schemas should be treated as an API:
- keep changes backward compatible where possible
- update the UI and any tests together
- avoid duplicating “mode mapping” logic here if it already exists in `../../config.py` or device controllers


