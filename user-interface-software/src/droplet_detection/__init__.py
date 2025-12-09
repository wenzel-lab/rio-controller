"""
Droplet Detection Module
Platform-agnostic droplet detection for Raspberry Pi (32-bit & 64-bit)
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
    PiCameraLegacy = None

try:
    from .pi_camera_v2 import PiCameraV2
    _V2_AVAILABLE = True
except ImportError:
    _V2_AVAILABLE = False
    PiCameraV2 = None

__all__ = ['BaseCamera', 'create_camera']

if _LEGACY_AVAILABLE:
    __all__.append('PiCameraLegacy')
if _V2_AVAILABLE:
    __all__.append('PiCameraV2')

