## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change UI behavior, routes, or WebSocket contracts, please update this document.

## Purpose

This folder contains the **web application layer** (Flask + templates/static assets + WebSocket handlers). It connects the browser UI to the device controllers.

## What belongs here / what does not

- **Belongs here**:
  - HTTP routes and template rendering (`routes.py`, `templates/`)
  - browser-side assets (`static/`)
  - WebSocket/HTTP handler code that translates UI actions into controller calls (`controllers/`)
- **Does not belong here**:
  - low-level hardware communication (belongs in `../drivers/`)
  - device orchestration/state machines (belongs in `../controllers/`)

## Key files

- `routes.py`: route registration and background update loop wiring
- `controllers/`: WebSocket/HTTP handlers (see `controllers/README.md`)
- `templates/`: HTML templates (primarily `index.html`)
- `static/`: JavaScript assets for UI behavior (ROI selector, histogram, etc.)

## Testing

Run routine tests from `software/`:

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```


