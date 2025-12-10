"""
Controller layer for the Rio microfluidics web application.

This package contains controllers that handle HTTP requests, WebSocket events,
and coordinate between the view and model layers following MVC architecture.

Modules:
    camera_controller: Camera and strobe control handlers
    flow_controller: Flow control handlers
    heater_controller: Heater control handlers
    view_model: View model formatters for template data
"""

# Use relative imports within the package
from .camera_controller import CameraController
from .flow_controller import FlowController
from .heater_controller import HeaterController
from .view_model import ViewModel

__all__ = ["CameraController", "FlowController", "HeaterController", "ViewModel"]
