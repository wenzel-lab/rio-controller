"""
View Model layer for formatting data for templates.

This module provides the ViewModel class which formats model data into
view-friendly structures, keeping presentation logic separate from business logic.

Classes:
    ViewModel: Formats device data for template rendering
"""

import logging
import sys
import os
from typing import Dict, List, Any, Optional

# Add parent directories to path for imports (software/ level)
software_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if software_root not in sys.path:
    sys.path.insert(0, software_root)
from controllers.flow_web import FlowWeb  # noqa: E402
from controllers.camera import Camera  # noqa: E402
from config import CONTROL_MODE_FIRMWARE_TO_UI  # noqa: E402

# Configure logging
logger = logging.getLogger(__name__)


class ViewModel:
    """
    View model formatter for template data.

    This class formats raw model data into structures suitable for template
    rendering, keeping presentation logic separate from business logic.
    """

    def __init__(self, flow: Optional[FlowWeb] = None, cam: Optional[Camera] = None):
        """
        Initialize the view model formatter.

        Args:
            flow: Optional FlowWeb instance (for backward compatibility)
            cam: Optional Camera instance (for backward compatibility)

        Note: These parameters are accepted for backward compatibility but are not
        required since all formatting methods are static and take their data as parameters.
        """
        self._flow = flow
        self._camera = cam

    @staticmethod
    def format_heater_data(heaters: List[Any]) -> List[Dict[str, Any]]:
        """
        Format heater data for template rendering.

        Args:
            heaters: List of heater_web instances

        Returns:
            List of dictionaries with formatted heater data
        """
        formatted = []
        for heater in heaters:
            try:
                formatted.append(
                    {
                        "status": heater.status_text,
                        "temp_text": heater.temp_text,
                        "temp_c_actual": heater.temp_c_actual,
                        "temp_c_target": heater.temp_c_target,
                        "pid_enabled": heater.pid_enabled,
                        "power_limit": heater.heat_power_limit_pc,
                        "autotune_status": heater.autotune_status_text,
                        "autotune_target_temp": heater.autotune_target_temp,
                        "autotuning": heater.autotuning,
                        "stir_speed_text": heater.stir_speed_text,
                        "stir_speed_target": heater.stir_target_speed,
                        "stir_enabled": heater.stir_enabled,
                    }
                )
            except Exception as e:
                logger.error(f"Error formatting heater data: {e}")
                formatted.append(
                    {
                        "status": "Error",
                        "temp_text": "",
                        "temp_c_actual": 0.0,
                        "temp_c_target": 0.0,
                        "pid_enabled": False,
                        "power_limit": 0,
                        "autotune_status": "",
                        "autotune_target_temp": 0.0,
                        "autotuning": False,
                        "stir_speed_text": "",
                        "stir_speed_target": 0,
                        "stir_enabled": False,
                    }
                )
        return formatted

    @staticmethod
    def format_flow_data(flow: FlowWeb) -> List[Dict[str, Any]]:
        """
        Format flow controller data for template rendering.

        Args:
            flow: FlowWeb instance

        Returns:
            List of dictionaries with formatted flow data for each channel
        """
        formatted = []
        try:
            # Get number of channels from flow controller
            if hasattr(flow, "flow") and hasattr(flow.flow, "NUM_CONTROLLERS"):
                num_channels = flow.flow.NUM_CONTROLLERS
            elif hasattr(flow, "control_modes") and flow.control_modes:
                num_channels = len(flow.control_modes)
            else:
                num_channels = 4  # Default fallback
            for i in range(num_channels):
                firmware_mode = flow.control_modes[i] if i < len(flow.control_modes) else 0
                ui_mode_index = CONTROL_MODE_FIRMWARE_TO_UI.get(firmware_mode, 0)

                formatted.append(
                    {
                        "status": flow.status_text[i] if i < len(flow.status_text) else "Unknown",
                        "pressure_mbar_text": (
                            flow.pressure_mbar_text[i] if i < len(flow.pressure_mbar_text) else ""
                        ),
                        "pressure_mbar_target": (
                            flow.pressure_mbar_targets[i]
                            if i < len(flow.pressure_mbar_targets)
                            else 0.0
                        ),
                        "flow_ul_hr_text": (
                            flow.flow_ul_hr_text[i] if i < len(flow.flow_ul_hr_text) else ""
                        ),
                        "flow_ul_hr_target": (
                            flow.flow_ul_hr_targets[i] if i < len(flow.flow_ul_hr_targets) else 0.0
                        ),
                        "control_modes": flow.CTRL_MODE_STR,  # Full list of available modes
                        "control_mode": ui_mode_index,  # Current mode index for UI
                    }
                )
        except Exception as e:
            logger.error(f"Error formatting flow data: {e}")
            # Return empty data structure
            for i in range(4):
                formatted.append(
                    {
                        "status": "Error",
                        "pressure_mbar_text": "",
                        "pressure_mbar_target": 0.0,
                        "flow_ul_hr_text": "",
                        "flow_ul_hr_target": 0.0,
                        "control_modes": ["Off", "Set Pressure", "Flow Closed Loop"],
                        "control_mode": 0,
                    }
                )
        return formatted

    @staticmethod
    def format_camera_data(camera: Camera) -> Dict[str, Any]:
        """
        Format camera data for template rendering.

        Args:
            camera: Camera instance

        Returns:
            Dictionary with formatted camera data
        """
        try:
            data = {
                "camera": camera.cam_data.get("camera", "none"),
                "status": camera.cam_data.get("status", ""),
            }
            # Add resolution information if available
            if hasattr(camera, "display_resolution"):
                data["display_width"] = camera.display_resolution[0]
                data["display_height"] = camera.display_resolution[1]
            if hasattr(camera, "snapshot_resolution_mode"):
                data["snapshot_resolution_mode"] = camera.snapshot_resolution_mode
            if hasattr(camera, "snapshot_resolution") and camera.snapshot_resolution:
                data["snapshot_width"] = camera.snapshot_resolution[0]
                data["snapshot_height"] = camera.snapshot_resolution[1]
            # Also include data from cam_data if it exists (for backward compatibility)
            if "display_width" in camera.cam_data:
                data["display_width"] = camera.cam_data["display_width"]
                data["display_height"] = camera.cam_data["display_height"]
            if "snapshot_resolution_mode" in camera.cam_data:
                data["snapshot_resolution_mode"] = camera.cam_data["snapshot_resolution_mode"]
            return data
        except Exception as e:
            logger.error(f"Error formatting camera data: {e}")
            return {"camera": "none", "status": "Error"}

    @staticmethod
    def format_strobe_data(camera: Camera) -> Dict[str, Any]:
        """
        Format strobe data for template rendering.

        Args:
            camera: Camera instance (contains strobe_data)

        Returns:
            Dictionary with formatted strobe data
        """
        try:
            return camera.strobe_data.copy()
        except Exception as e:
            logger.error(f"Error formatting strobe data: {e}")
            return {
                "hold": 0,
                "enable": 0,
                "wait_ns": 0,
                "period_ns": 100000,
                "framerate": 0,
                "cam_read_time_us": 0,
            }

    @staticmethod
    def format_debug_data(update_count: int) -> Dict[str, Any]:
        """
        Format debug data for template rendering.

        Args:
            update_count: Current update counter

        Returns:
            Dictionary with formatted debug data
        """
        return {"update_count": update_count}
