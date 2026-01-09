"""
Centralized sys.path setup for runtime and tests.

Goal (Track 4): avoid per-module path mutations. Call bootstrap_runtime() once in
the app entrypoint, and bootstrap_tests() once in test setup. This keeps imports
beginner-friendly for hardware folks: run `python main.py` from `software/` or
`RIO_SIMULATION=true python -m pytest` and imports will resolve without per-file
sys.path hacks.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _add_path(p: Path) -> None:
    s = str(p)
    if s not in sys.path:
        sys.path.append(s)


def bootstrap_runtime() -> None:
    """
    Add the minimum set of repo paths needed for runtime imports.

    - software/               (controllers, drivers, simulation, etc.)
    - software/rio-webapp/    (web templates/static and python helpers)
    - software/rio-webapp/controllers/ (web controllers)
    """

    software_dir = Path(__file__).resolve().parent
    _add_path(software_dir)

    rio_webapp_dir = software_dir / "rio-webapp"
    _add_path(rio_webapp_dir)

    rio_webapp_controllers_dir = rio_webapp_dir / "controllers"
    _add_path(rio_webapp_controllers_dir)


def bootstrap_tests() -> None:
    """
    Test bootstrap: same as runtime, so tests can import controllers/web layers
    without local sys.path edits.
    """

    bootstrap_runtime()
