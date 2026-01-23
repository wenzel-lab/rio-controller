"""Droplet detection controller Thing for LabThings/WoT."""

import logging
from typing import TYPE_CHECKING

import labthings_fastapi as lt

# Handle Thing import with fallback
Thing = None
try:
    Thing = lt.Thing
except AttributeError:
    # Try alternate import path
    try:
        from labthings_fastapi.thing import Thing
    except (ImportError, AttributeError):
        # Fallback - create a simple base class
        class Thing:
            """Fallback Thing base class for when labthings_fastapi.Thing is unavailable."""
            def __init__(self, thing_server_interface=None):
                self.thing_server_interface = thing_server_interface

# Handle decorators with fallback
property_decorator = None
action_decorator = None
try:
    property_decorator = lt.property
    action_decorator = lt.action
except AttributeError:
    # Fallback decorators that do nothing
    def property_decorator(func):
        return func
    
    def action_decorator(func):
        return func

# Handle InvocationError import with fallback
InvocationError = None
try:
    from labthings_fastapi.exceptions import InvocationError
except (ImportError, AttributeError):
    # Fallback if labthings_fastapi doesn't have exceptions module
    InvocationError = Exception

if TYPE_CHECKING:
    from controllers.droplet_detector_controller import DropletDetectorController

logger = logging.getLogger(__name__)


class DropletThing(Thing):
    """Droplet detection controller Thing.

    Exposes droplet detection control and statistics as WoT-compliant properties and actions.
    """

    title = "Droplet Detection Controller"

    def __init__(
        self, droplet_controller: "DropletDetectorController", thing_server_interface=None
    ):
        """Initialize DropletThing with a DropletDetectorController.

        Args:
            droplet_controller: DropletDetectorController instance
            thing_server_interface: LabThings server interface (provided by ThingServer)
        """
        super().__init__(thing_server_interface)
        self._droplet = droplet_controller

    @property_decorator
    def status(self) -> dict:
        """Get current droplet detection status.

        Returns:
            Dictionary with running, frame_count, droplet_count_total, processing_rate_hz
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return {
            "running": self._droplet.running,
            "frame_count": self._droplet.frame_count,
            "droplet_count_total": self._droplet.droplet_count_total,
            "processing_rate_hz": round(getattr(self._droplet, "processing_rate_hz", 0.0), 2),
        }

    @property_decorator
    def statistics(self) -> dict:
        """Get droplet detection statistics.

        Returns:
            Dictionary with statistical data
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return self._droplet.get_statistics()

    @property_decorator
    def histogram(self) -> dict:
        """Get droplet size histogram.

        Returns:
            Dictionary with histogram data
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return self._droplet.get_histogram()

    @property_decorator
    def performance(self) -> dict:
        """Get performance metrics.

        Returns:
            Dictionary with performance data
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return self._droplet.get_performance_metrics()

    @action_decorator
    def start(self) -> dict:
        """Start droplet detection.

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If controller unavailable or start failed
        """
        if self._droplet is None:
            raise InvocationError("Droplet controller unavailable")

        ok = self._droplet.start()
        if not ok:
            raise InvocationError("Failed to start droplet detection (check ROI)")
        return {"ok": True}

    @action_decorator
    def stop(self) -> dict:
        """Stop droplet detection.

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If controller unavailable
        """
        if self._droplet is None:
            raise InvocationError("Droplet controller unavailable")

        self._droplet.stop()
        return {"ok": True}
