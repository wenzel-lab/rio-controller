"""Droplet detection controller Thing for LabThings/WoT."""

import logging
from typing import TYPE_CHECKING

import labthings_fastapi as lt
try:
    from labthings_fastapi.exceptions import InvocationError
except ModuleNotFoundError:  # pragma: no cover - older labthings versions
    class InvocationError(RuntimeError):
        """Fallback invocation error for older labthings-fastapi versions."""

if TYPE_CHECKING:
    from controllers.droplet_detector_controller import DropletDetectorController

logger = logging.getLogger(__name__)


class DropletThing(lt.Thing):
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

    @lt.property
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

    @lt.property
    def statistics(self) -> dict:
        """Get droplet detection statistics.

        Returns:
            Dictionary with statistical data
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return self._droplet.get_statistics()

    @lt.property
    def histogram(self) -> dict:
        """Get droplet size histogram.

        Returns:
            Dictionary with histogram data
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return self._droplet.get_histogram()

    @lt.property
    def performance(self) -> dict:
        """Get performance metrics.

        Returns:
            Dictionary with performance data
        """
        if self._droplet is None:
            raise RuntimeError("Droplet controller unavailable")

        return self._droplet.get_performance_metrics()

    @lt.action
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

    @lt.action
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
