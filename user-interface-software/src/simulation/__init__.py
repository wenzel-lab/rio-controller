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
from .camera_simulated import SimulatedCamera
from .spi_simulated import SimulatedSPIHandler
from .strobe_simulated import SimulatedStrobe
from .flow_simulated import SimulatedFlow

__all__ = [
    'SimulationConfig',
    'load_config',
    'SimulatedCamera',
    'SimulatedSPIHandler',
    'SimulatedStrobe',
    'SimulatedFlow',
]

