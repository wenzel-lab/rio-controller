# API development log

This log records implementation steps for the new network API layer (branch: `new-api`).

## 2026-01-09 — Step 1 skeleton

- Added `software/api/` package with:
  - `main.py` (FastAPI skeleton; `/api/system/health`, `/api/system/capabilities`)
  - `config.py` (API settings; host/port/CORS/auth token placeholder; honors `RIO_SIMULATION`)
  - `schemas.py` (health/capabilities models)
  - `__init__.py` (interface-layer notice)
- Added `software/requirements-api.txt` with pinned API deps (`fastapi==0.95.2`, `uvicorn[standard]==0.21.1`, `labthings-fastapi==0.0.6`, `pydantic==1.10.14`, `typing_extensions>=4.7.0`).
- Updated `software/README.md` to list the experimental API and how to run the skeleton.
- Wired controllers into API skeleton (v0.2.0):
  - `api.main` now bootstraps runtime, initializes SPI, and instantiates FlowWeb, heater_web, Camera/PiStrobeCam (with DummySocketIO), and optional droplet controller (if enabled). Capabilities now reflect actual init success.
- Deployment: `create-pi-deployment.sh` now copies `requirements-api.txt` and installs it if present.

Notes:
- Controllers are not yet wired into the API; capabilities are placeholder. Future steps will instantiate controllers and Things.
- API default port is 5001 (`RIO_API_PORT` override).

## 2026-01-09 — Initial REST wiring (flow/heater/camera snapshot)

- `api.main`: now boots runtime, initializes SPI, instantiates controllers (FlowWeb, heater_web x4, Camera/PiStrobeCam, optional droplet); capabilities reflect actual init success.
- Added initial REST endpoints:
  - `GET /api/control/flow/state`
  - `POST /api/control/flow/set_pressure`, `/set_flow`, `/set_mode`, `/set_pi_consts`
  - `GET /api/control/heater/state`
  - `POST /api/control/heater/set_temp`, `/pid`, `/stir`
  - `GET /api/streams/camera/snapshot`
- Added request/response models in `api.schemas` for flow/heater state and setters.
- Deployment remains unchanged from previous step (requirements-api included).

## 2026-01-09 — Channel metadata endpoints

- Added channel metadata models and in-memory config:
  - `GET /api/config/channels`
  - `POST /api/config/channels` (merge patch for enable/name per channel, topics: flow/pressure/heater)
- Updated `api.schemas` with channel models.


