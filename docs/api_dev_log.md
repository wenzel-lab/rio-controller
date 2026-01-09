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

Notes:
- Controllers are not yet wired into the API; capabilities are placeholder. Future steps will instantiate controllers and Things.
- API default port is 5001 (`RIO_API_PORT` override).


