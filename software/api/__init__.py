"""
API interface package for Rio.

This layer is an interface-only adapter (FastAPI/LabThings), not a place for
device logic. It should import existing controllers and expose them over HTTP
and WebSocket, keeping controllers/drivers as the source of truth.
"""
