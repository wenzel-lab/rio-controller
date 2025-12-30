"""
Configuration constants for the Rio microfluidics controller.

This module centralizes all configuration values, magic numbers, and constants
used throughout the application to improve maintainability and readability.
"""

import os

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
    "1920x1080": (1920, 1080),
}

# Maximum sensor resolutions
CAMERA_V2_MAX_WIDTH = 3280  # Raspberry Pi Camera V2 (Sony IMX219)
CAMERA_V2_MAX_HEIGHT = 2464
CAMERA_HQ_MAX_WIDTH = 4056  # Raspberry Pi HQ Camera (Sony IMX477) - approximate
CAMERA_HQ_MAX_HEIGHT = 3040

# Snapshot Resolution Modes
SNAPSHOT_RESOLUTION_DISPLAY = "display"  # Use current display resolution
SNAPSHOT_RESOLUTION_FULL = "full"  # Use full sensor resolution
SNAPSHOT_RESOLUTION_CUSTOM = "custom"  # Use custom resolution

# Strobe Configuration
STROBE_DEFAULT_PERIOD_NS = 20000  # 20 microseconds
STROBE_MAX_PERIOD_NS = 16000000  # 16 milliseconds
STROBE_PRE_PADDING_NS = 32  # Pre-padding before strobe pulse
STROBE_POST_PADDING_NS = 20000000  # Post-padding after strobe pulse
STROBE_TRIGGER_PULSE_US = 0.000001  # 1 microsecond trigger pulse
STROBE_TRIGGER_GPIO_PIN = 18  # GPIO pin for PIC trigger (BCM numbering)
STROBE_REPLY_PAUSE_S = 0.1  # SPI reply pause time

# Strobe Control Mode
# Options: "strobe-centric" (software trigger) or "camera-centric" (hardware trigger)
# strobe-centric: Strobe timing controls camera exposure (works with old firmware)
#                 Note: Only available on 32-bit due to camera package limitations (picamera)
#                 Replaced by camera-centric mode with new strobe chip firmware
# camera-centric: Camera frame callback triggers strobe via GPIO (requires new firmware with hardware trigger)
# Can be overridden via environment variable RIO_STROBE_CONTROL_MODE
STROBE_CONTROL_MODE = os.getenv(
    "RIO_STROBE_CONTROL_MODE", "camera-centric"
).lower()  # Default to "camera-centric" for strobe-rewrite branch
STROBE_CONTROL_MODE_STROBE_CENTRIC = "strobe-centric"  # Strobe-centric control (software trigger)
STROBE_CONTROL_MODE_CAMERA_CENTRIC = "camera-centric"  # Camera trigger-centric (hardware trigger)
# Backward compatibility aliases (deprecated - use strobe-centric/camera-centric)
STROBE_CONTROL_MODE_LEGACY = "strobe-centric"  # Alias for strobe-centric
STROBE_CONTROL_MODE_NEW = "camera-centric"  # Alias for camera-centric

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
# Firmware control modes: 0=Off, 1=Pressure Open Loop, 2=Pressure Closed Loop (deprecated), 3=Flow Closed Loop
# UI control modes: 0=Off, 1=Set Pressure, 2=Flow Closed Loop
CONTROL_MODE_FIRMWARE_TO_UI = {
    0: 0,  # Off -> Off
    1: 1,  # Pressure Open Loop -> Set Pressure
    2: 0,  # Pressure Closed Loop (hidden) -> Off
    3: 2,  # Flow Closed Loop -> Flow Closed Loop
}

CONTROL_MODE_UI_TO_FIRMWARE = {
    0: 0,  # Off -> Off
    1: 1,  # Set Pressure -> Pressure Open Loop
    2: 3,  # Flow Closed Loop -> Flow Closed Loop
}

# Camera Types
CAMERA_TYPE_NONE = "none"
CAMERA_TYPE_RPI = "rpi"
CAMERA_TYPE_RPI_HQ = "rpi_hq"
CAMERA_TYPE_MAKO = "mako"

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
CMD_SET_CONFIG = "set_config"
CMD_SET_RESOLUTION = "set_resolution"
CMD_SET_SNAPSHOT_RESOLUTION = "set_snapshot_resolution"
CMD_HOLD = "hold"
CMD_ENABLE = "enable"
CMD_TIMING = "timing"
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
