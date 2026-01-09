"""
Rio API server (skeleton).

- Provides minimal /api/system/health and /api/system/capabilities endpoints.
- Designed to run alongside the existing Flask UI, but only one process should
  own hardware. The API can be the hardware-owning process; the UI can call it
  via adapters (future step).

This file intentionally avoids controller wiring for now; later steps will
instantiate controllers and Things.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.schemas import HealthResponse, CapabilitiesResponse


def create_app() -> FastAPI:
    app = FastAPI(title="Rio API", version="0.1.0 (skeleton)")

    if settings.cors_allow_all:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/system/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", simulation=settings.simulation)

    @app.get("/api/system/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        # Placeholder; will be populated from controllers in later steps.
        modules = {
            "flow": True,
            "pressure": True,
            "heater": True,
            "strobe": True,
            "camera": True,
            "droplet": True,
            "pump": False,
        }
        notes = {"warning": "Capabilities are static placeholders in the skeleton API."}
        return CapabilitiesResponse(modules=modules, simulation=settings.simulation, notes=notes)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


