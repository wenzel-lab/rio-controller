"""
Configuration constants for the Rio microfluidics controller.

This module centralizes all configuration values, magic numbers, and constants
used throughout the application to improve maintainability and readability.
"""

# Camera Configuration
CAMERA_DEFAULT_WIDTH = 640
CAMERA_DEFAULT_HEIGHT = 480
CAMERA_DEFAULT_FPS = 30
CAMERA_THREAD_WIDTH = 1024
CAMERA_THREAD_HEIGHT = 768
CAMERA_THREAD_FPS = 30
CAMERA_INIT_TIMEOUT_S = 5.0  # Timeout for camera initialization
CAMERA_FRAME_WAIT_SLEEP_S = 0.01  # Sleep interval while waiting for first frame

# Strobe Configuration
STROBE_DEFAULT_PERIOD_NS = 100000  # 100 microseconds
STROBE_MAX_PERIOD_NS = 16000000  # 16 milliseconds
STROBE_PRE_PADDING_NS = 32  # Pre-padding before strobe pulse
STROBE_POST_PADDING_NS = 20000000  # Post-padding after strobe pulse
STROBE_TRIGGER_PULSE_US = 0.000001  # 1 microsecond trigger pulse
STROBE_TRIGGER_GPIO_PIN = 18  # GPIO pin for PIC trigger (BCM numbering)
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
