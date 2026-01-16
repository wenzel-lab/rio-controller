"""
Camera driver module.

Provides camera abstraction layer and backends:
- PiCameraLegacy: Raspberry Pi camera (32-bit OS, legacy picamera)
- MakoCamera: Allied Vision Mako (Vimba SDK)
- DahengCamera: Daheng MER2 (gxipy SDK)
"""

from .camera_base import BaseCamera, create_camera

# Import camera implementations lazily (only when needed)
# This avoids import errors when hardware libraries aren't available (e.g., on Mac/PC)
# The create_camera() function will import these when actually needed
try:
    from .pi_camera_legacy import PiCameraLegacy

    _LEGACY_AVAILABLE = True
except ImportError:
    _LEGACY_AVAILABLE = False
    PiCameraLegacy = None  # type: ignore[assignment, misc]

try:
    from .mako_camera import MakoCamera

    _MAKO_AVAILABLE = True
except ImportError:
    _MAKO_AVAILABLE = False
    MakoCamera = None  # type: ignore[assignment, misc]


try:
    from .daheng_camera import DahengCamera

    _DAHENG_AVAILABLE = True
except ImportError:
    _DAHENG_AVAILABLE = False
    DahengCamera = None  # type: ignore[assignment, misc]

__all__ = ["BaseCamera", "create_camera"]

if _LEGACY_AVAILABLE:
    __all__.append("PiCameraLegacy")
if _MAKO_AVAILABLE:
    __all__.append("MakoCamera")
if _DAHENG_AVAILABLE:
    __all__.append("DahengCamera")
