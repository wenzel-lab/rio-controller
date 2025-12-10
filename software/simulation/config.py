"""
Configuration system for simulation mode.

Supports YAML configuration files and environment variables.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

# YAML is optional - config can work with just environment variables
try:
    import yaml  # type: ignore[import-untyped]

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class SimulationConfig:
    """Configuration for simulation mode."""

    # Global simulation flag
    simulation: bool = False

    # Camera simulation settings
    camera: Dict[str, Any] = field(
        default_factory=lambda: {
            "width": 640,
            "height": 480,
            "fps": 30,
            "generate_droplets": True,
            "droplet_count": 5,
            "droplet_size_range": (10, 50),  # pixels
        }
    )

    # Strobe simulation settings
    strobe: Dict[str, Any] = field(
        default_factory=lambda: {
            "port": 24,
            "reply_pause_s": 0.1,
            "simulate_timing": True,
        }
    )

    # Flow simulation settings
    flow: Dict[str, Any] = field(
        default_factory=lambda: {
            "port": 26,
            "reply_pause_s": 0.1,
            "num_channels": 4,
            "pressure_range": (0, 6000),  # mbar
            "flow_range": (0, 1000),  # ul/hr
        }
    )

    # SPI simulation settings
    spi: Dict[str, Any] = field(
        default_factory=lambda: {
            "bus": 0,
            "mode": 2,
            "speed_hz": 30000,
        }
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationConfig":
        """Create config from dictionary."""
        return cls(
            simulation=data.get("simulation", False),
            camera=data.get("camera", {}),
            strobe=data.get("strobe", {}),
            flow=data.get("flow", {}),
            spi=data.get("spi", {}),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> "SimulationConfig":
        """Load config from YAML file."""
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required to load YAML config files. Install with: pip install PyYAML"
            )
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    @classmethod
    def from_env(cls) -> "SimulationConfig":
        """Load config from environment variables."""
        simulation = os.getenv("RIO_SIMULATION", "false").lower() == "true"
        return cls(simulation=simulation)


def load_config(config_path: Optional[Path] = None) -> SimulationConfig:
    """
    Load simulation configuration.

    Priority:
    1. YAML file (if provided)
    2. Environment variable RIO_SIMULATION
    3. Default (simulation=False)

    Args:
        config_path: Optional path to YAML config file

    Returns:
        SimulationConfig instance
    """
    # Try YAML file first
    if config_path and config_path.exists():
        try:
            return SimulationConfig.from_yaml(config_path)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")

    # Try environment variable
    if os.getenv("RIO_SIMULATION"):
        return SimulationConfig.from_env()

    # Default
    return SimulationConfig()
