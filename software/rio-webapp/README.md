# software/rio-webapp/ — Flask UI (routes + templates + static assets)

This folder is the web-facing layer: Flask routes, Socket.IO integration, HTML templates, and browser-side JavaScript. It translates user actions in the browser into calls on the **device controllers** in `../controllers/`.

## What’s inside

- **`routes.py`**
  - `register_routes(...)` wires:
    - the main HTML page (`/`)
    - the MJPEG stream endpoint (`/video`)
    - optional droplet-detection API endpoints under `/api/droplet/*` (only if the droplet controller is enabled)

- **`controllers/`**
  - Socket.IO event handlers (see `controllers/README.md`)
  - these handlers parse `cmd`/`parameters` payloads and call into `../controllers/*`

- **`templates/`**
  - server-rendered HTML, primarily `index.html`
  - `index.html` conditionally shows droplet UI sections when `droplet_analysis_enabled` is true

- **`static/`**
  - browser-side JavaScript (ROI selection widgets, droplet histogram rendering, etc.)
  - current template usage (as of this commit):
    - ROI selector script loaded by `templates/index.html` is `static/roi_selector_range.js`
    - droplet histogram rendering is `static/droplet_histogram.js`

## Interfaces to other layers (where the boundaries are)

- **Calls into**: `software/controllers/*` (camera/flow/heater/droplet control)
- **Does not call into**: low-level SPI/camera backends directly (those are in `../drivers/`)
- **Owns**: event names/payloads that the browser and server agree on (Socket.IO contract)

## Testing

Run routine tests from `software/` (simulation mode unless explicitly testing on hardware):

```bash
cd software
export RIO_SIMULATION=true
pytest -v
```

## AI-generated notice

This file was AI-generated and may contain errors. Please verify against the source code and runtime behavior.
- Date: 2025-12-30
- Model: GPT-5.2
- Maintenance: If you change routes, templates, or Socket.IO event names/payloads, update this document.


