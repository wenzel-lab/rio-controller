"""
Simulation module for Rio controller.

Provides simulated hardware implementations for testing and development
without requiring physical Raspberry Pi or hardware modules.

Usage:
    Set simulation mode in config.yaml:
        simulation: true
    
    Or via environment variable:
        export RIO_SIMULATION=true
"""

from .config import SimulationConfig, load_config
from .spi_simulated import SimulatedSPIHandler
from .strobe_simulated import SimulatedStrobe
from .flow_simulated import SimulatedFlow

# Camera simulation requires numpy/opencv - import lazily
try:
    from .camera_simulated import SimulatedCamera
    _CAMERA_AVAILABLE = True
except ImportError:
    _CAMERA_AVAILABLE = False
    SimulatedCamera = None

__all__ = [
    'SimulationConfig',
    'load_config',
    'SimulatedSPIHandler',
    'SimulatedStrobe',
    'SimulatedFlow',
]

if _CAMERA_AVAILABLE:
    __all__.append('SimulatedCamera')

