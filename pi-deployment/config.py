"""
Configuration constants for the Rio microfluidics controller.

This module centralizes all configuration values, magic numbers, and constants
used throughout the application to improve maintainability and readability.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from controllers.flow_control_modes import (  # single source-of-truth (Phase B / Track 2)
    CONTROL_MODE_FIRMWARE_TO_UI,
    CONTROL_MODE_UI_TO_FIRMWARE,
    FLOW_CTRL_MODE_STR,
)

# Re-export control mode mappings for backward compatibility.
_CONTROL_MODE_EXPORTS = (
    CONTROL_MODE_FIRMWARE_TO_UI,
    CONTROL_MODE_UI_TO_FIRMWARE,
    FLOW_CTRL_MODE_STR,
)

# YAML is optional; runtime config falls back to env-only if unavailable.
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    YAML_AVAILABLE = False

# Camera Configuration
CAMERA_DEFAULT_WIDTH = 640
CAMERA_DEFAULT_HEIGHT = 480
CAMERA_DEFAULT_FPS = 30
CAMERA_THREAD_WIDTH = 1024
CAMERA_THREAD_HEIGHT = 768
CAMERA_THREAD_FPS = 30
CAMERA_DISPLAY_FPS = 10  # Display frame rate (for web streaming, lower to reduce Pi load)
CAMERA_INIT_TIMEOUT_S = 5.0  # Timeout for camera initialization
CAMERA_FRAME_WAIT_SLEEP_S = 0.01  # Sleep interval while waiting for first frame

# Camera Resolution Presets
# Predefined resolution presets for display/streaming (width, height)
CAMERA_RESOLUTION_PRESETS = {
    "640x480": (640, 480),
    "800x600": (800, 600),
    "1024x768": (1024, 768),
    "1280x960": (1280, 960),
    "1440x1080": (1440, 1080),  # Daheng MER2 full sensor
    "1920x1080": (1920, 1080),
}

# Maximum sensor resolutions (legacy Pi camera V2)
CAMERA_V2_MAX_WIDTH = 3280  # Raspberry Pi Camera V2 (Sony IMX219)
CAMERA_V2_MAX_HEIGHT = 2464

# Snapshot Resolution Modes
SNAPSHOT_RESOLUTION_DISPLAY = "display"  # Use current display resolution
SNAPSHOT_RESOLUTION_FULL = "full"  # Use full sensor resolution
SNAPSHOT_RESOLUTION_CUSTOM = "custom"  # Use custom resolution

# Strobe Configuration
# Use BOARD numbering to stay consistent with other GPIO users (SPI handler pins use BOARD)
# Pin 12 (board) == BCM 18
STROBE_DEFAULT_PERIOD_NS = 100000  # 100 microseconds (legacy PiStrobeCam default; visible free-run)
STROBE_MAX_PERIOD_NS = 16000000  # 16 milliseconds (PIC timer max ≈ 16.32 ms)
STROBE_PIC_MAX_TIME_NS = 16320000  # firmware MAX_TIME_NS for wait/duration
STROBE_PRE_PADDING_NS = 32  # Pre-padding before strobe pulse
STROBE_POST_PADDING_NS = 20000000  # Post-padding after strobe pulse (legacy fps calc)
STROBE_VISIBLE_MAX_HZ = 60  # Match old PiCamera clamp — free-run blink rate cap
STROBE_REPLY_PAUSE_S = 0.1  # SPI reply pause time

# Flow Control Configuration
FLOW_REPLY_PAUSE_S = 0.1  # SPI reply pause time for flow controller
FLOW_NUM_CONTROLLERS = 4  # Number of flow controller channels

# Heater Configuration
HEATER_NUM_UNITS = 4  # Number of heater units
HEATER_REPLY_PAUSE_S = 0.05  # SPI reply pause time for heaters
HEATER_INIT_TRIES = 3  # Number of initialization attempts

# SPI Configuration
SPI_BUS = 0
SPI_MODE = 2
SPI_SPEED_HZ = 30000

# Background Thread Configuration
BACKGROUND_UPDATE_INTERVAL_S = 1.0  # Update interval for background thread

# ROI Configuration
ROI_MIN_SIZE_PX = 10  # Minimum ROI size in pixels
ROI_UPDATE_INTERVAL_MS = 500  # ROI info update interval

# Control Mode Mapping
# NOTE: Imported from `software/flow_control_modes.py` and re-exported here for
# backward compatibility. UI strings live alongside the mappings.

# Camera Types
CAMERA_TYPE_NONE = "none"
CAMERA_TYPE_RPI = "rpi"
CAMERA_TYPE_MAKO = "mako"
CAMERA_TYPE_DAHENG = "daheng"

# File Paths
SNAPSHOT_FOLDER = "home/pi/snapshots/"
SNAPSHOT_FILENAME_PREFIX = "snapshot_"
SNAPSHOT_FILENAME_SUFFIX = ".jpg"

# FPS Optimization
FPS_OPTIMIZATION_MAX_TRIES = 10
FPS_OPTIMIZATION_CONVERGENCE_THRESHOLD_US = 1000  # Convergence threshold in microseconds
FPS_OPTIMIZATION_POST_PADDING_OFFSET_US = 100  # Additional padding offset

# Image Quality Configuration
# Different quality settings for streaming (lower) vs snapshots (higher)
# Lower streaming quality reduces bandwidth and CPU usage significantly
# Quality range: 1-100 (1=lowest quality/smallest file, 100=highest quality/largest file)
_streaming_quality_raw = int(os.getenv("RIO_JPEG_QUALITY_STREAMING", "75"))
CAMERA_STREAMING_JPEG_QUALITY = max(
    1, min(100, _streaming_quality_raw)
)  # Clamp to valid range [1, 100]

_snapshot_quality_raw = int(os.getenv("RIO_JPEG_QUALITY_SNAPSHOT", "95"))
CAMERA_SNAPSHOT_JPEG_QUALITY = max(
    1, min(100, _snapshot_quality_raw)
)  # Clamp to valid range [1, 100]

# ROI Mode (software default; hardware optional if supported by camera backend)
ROI_MODE_SOFTWARE = "software"
ROI_MODE_HARDWARE = "hardware"
ROI_MODE = os.getenv("RIO_ROI_MODE", ROI_MODE_SOFTWARE).strip().lower() or ROI_MODE_SOFTWARE

# Syringe pump configuration (USB serial by default)
PUMP_ENABLED = os.getenv("RIO_PUMP_ENABLED", "false").lower() == "true"
PUMP_PORT = os.getenv("RIO_PUMP_PORT", "").strip() or None
PUMP_BAUDRATE = int(os.getenv("RIO_PUMP_BAUDRATE", "115200"))
PUMP_TIMEOUT_S = float(os.getenv("RIO_PUMP_TIMEOUT_S", "1.0"))
PUMP_WRITE_TIMEOUT_S = float(os.getenv("RIO_PUMP_WRITE_TIMEOUT_S", "1.0"))

# Runtime config (YAML + env) for backend selection
CONFIG_FILE_PATH = os.getenv("RIO_CONFIG_FILE", "rio-config.yaml")


def _normalize_backend(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in ("simulation", "sim"):
        return "simulation"
    if normalized in ("hardware", "hw", "real"):
        return "hardware"
    return None


def _parse_module_backend_overrides(raw: str) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        module, backend = pair.split("=", 1)
        module_key = module.strip().lower()
        backend_key = _normalize_backend(backend)
        if module_key and backend_key:
            overrides[module_key] = backend_key
    return overrides


def load_runtime_config() -> Dict[str, Any]:
    """Load runtime backend config from YAML, if available."""
    if not YAML_AVAILABLE:
        return {}
    config_path = Path(CONFIG_FILE_PATH)
    if not config_path.exists():
        return {}
    try:
        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        return {}
    runtime = data.get("runtime")
    return runtime if isinstance(runtime, dict) else {}


def resolve_default_backend(runtime_config: Optional[Dict[str, Any]] = None) -> str:
    """Resolve the default backend (simulation|hardware) with env overrides."""
    env_default = _normalize_backend(os.getenv("RIO_DEFAULT_BACKEND"))
    if env_default:
        return env_default
    if "RIO_SIMULATION" in os.environ:
        return (
            "simulation" if os.getenv("RIO_SIMULATION", "false").lower() == "true" else "hardware"
        )
    runtime_config = runtime_config or load_runtime_config()
    cfg_default = _normalize_backend(
        runtime_config.get("default_backend") if isinstance(runtime_config, dict) else None
    )
    if cfg_default:
        return cfg_default
    return "hardware"


def resolve_module_backend(module: str, runtime_config: Optional[Dict[str, Any]] = None) -> str:
    """Resolve per-module backend (simulation|hardware), falling back to default."""
    overrides = _parse_module_backend_overrides(os.getenv("RIO_MODULE_BACKENDS", ""))
    module_key = module.strip().lower()
    if module_key in overrides:
        return overrides[module_key]
    runtime_config = runtime_config or load_runtime_config()
    modules = runtime_config.get("modules") if isinstance(runtime_config, dict) else None
    if isinstance(modules, dict):
        cfg_value = _normalize_backend(modules.get(module_key))
        if cfg_value:
            return cfg_value
    return resolve_default_backend(runtime_config)


# Logging Configuration
# Production should use WARNING level to reduce I/O overhead
# Development can use INFO or DEBUG for more verbose output
# Set via environment variable: RIO_LOG_LEVEL (INFO, DEBUG, WARNING, ERROR)
RIO_LOG_LEVEL = os.getenv("RIO_LOG_LEVEL", "WARNING").upper()  # Default: WARNING for production

# WebSocket Events
WS_EVENT_CAM = "cam"
WS_EVENT_STROBE = "strobe"
WS_EVENT_ROI = "roi"
WS_EVENT_HEATER = "heater"
WS_EVENT_FLOW = "flow"
WS_EVENT_DEBUG = "debug"
WS_EVENT_RELOAD = "reload"

# WebSocket Commands
CMD_SELECT = "select"
CMD_SNAPSHOT = "snapshot"
CMD_OPTIMIZE = "optimize"
CMD_RECORD_ROI_FRAMES = "record_roi_frames"
CMD_SET_CONFIG = "set_config"
CMD_SET_EXPOSURE = "set_exposure"
CMD_SET_RESOLUTION = "set_resolution"
CMD_SET_SNAPSHOT_RESOLUTION = "set_snapshot_resolution"
CMD_HOLD = "hold"
CMD_ENABLE = "enable"
CMD_TIMING = "timing"
CMD_TRIGGER_MODE = "trigger_mode"
CMD_SET = "set"
CMD_GET = "get"
CMD_CLEAR = "clear"
CMD_TEMP_C_TARGET = "temp_c_target"
CMD_PID_ENABLE = "pid_enable"
CMD_POWER_LIMIT_PC = "power_limit_pc"
CMD_AUTOTUNE = "autotune"
CMD_STIR = "stir"
CMD_PRESSURE_MBAR_TARGET = "pressure_mbar_target"
CMD_FLOW_UL_HR_TARGET = "flow_ul_hr_target"
CMD_CONTROL_MODE = "control_mode"
CMD_FLOW_PI_CONSTS = "flow_pi_consts"
