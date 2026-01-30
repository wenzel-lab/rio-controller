"""Compatibility helpers for LabThings FastAPI on Pydantic 2.x."""

from __future__ import annotations

import inspect
from typing import Any, Optional


def apply_labthings_pydantic_patch() -> None:
    """Patch LabThings 0.0.6 to work with newer Pydantic create_model API."""

    try:
        from pydantic import ConfigDict, create_model
    except Exception:
        return

    try:
        import labthings_fastapi.utilities.introspection as introspection
    except Exception:
        return

    if getattr(introspection, "_patched_model_config", False):
        return

    if "model_config" in inspect.signature(create_model).parameters:
        # Newer Pydantic already supports model_config; no patch needed.
        return

    def create_model_compat(
        model_name: str,
        *,
        model_config: Optional[ConfigDict] = None,
        __config__: Optional[ConfigDict] = None,
        **field_definitions: Any,
    ):
        if model_config is not None and __config__ is None:
            __config__ = model_config
        return create_model(model_name, __config__=__config__, **field_definitions)

    introspection.create_model = create_model_compat
    introspection._patched_model_config = True
