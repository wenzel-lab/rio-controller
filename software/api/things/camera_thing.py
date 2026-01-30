"""Camera and strobe controller Thing for LabThings/WoT."""

import logging
from typing import TYPE_CHECKING, Any, Optional

import labthings_fastapi as lt
from labthings_fastapi import decorators as lt_decorators

lt_action = getattr(lt_decorators, "action", None) or lt_decorators.thing_action
lt_property = getattr(lt_decorators, "property", None) or lt_decorators.thing_property
from labthings_fastapi import thing as lt_thing
try:
    from labthings_fastapi.exceptions import InvocationError
except ModuleNotFoundError:  # pragma: no cover - older labthings versions
    class InvocationError(RuntimeError):
        """Fallback invocation error for older labthings-fastapi versions."""
try:
    from labthings_fastapi.outputs.blob import Blob
except ImportError:  # pragma: no cover - labthings-fastapi 0.0.6
    from labthings_fastapi.outputs.blob import BlobOutput as Blob

from config import (
    CMD_SET_RESOLUTION,
    CMD_SET_SNAPSHOT_RESOLUTION,
    CMD_SET,
    CMD_CLEAR,
    CMD_ENABLE,
    CMD_HOLD,
    CMD_TIMING,
)

if TYPE_CHECKING:
    from controllers.camera import Camera

logger = logging.getLogger(__name__)


class JPEGBlob(Blob):
    """Blob subclass for JPEG images."""

    media_type: str = "image/jpeg"


class CameraThing(lt_thing.Thing):
    """Camera and strobe controller Thing.

    Exposes camera control (resolution, ROI, snapshot) and strobe control as WoT-compliant actions.
    """

    title = "Camera and Strobe Controller"

    def __init__(self, camera: "Camera", thing_server_interface=None):
        """Initialize CameraThing with a Camera controller.

        Args:
            camera: Camera controller instance
            thing_server_interface: LabThings server interface (provided by ThingServer)
        """
        super().__init__(thing_server_interface)
        self._camera = camera

    @lt_action
    def snapshot(self) -> Blob:
        """Capture a single frame from the camera.

        Returns:
            Blob containing JPEG image data

        Raises:
            InvocationError: If camera unavailable or no frame available
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        if self._camera.thread is None or not self._camera.thread.is_alive():
            self._camera.initialize()

        frame = self._camera.get_frame()
        if not frame:
            raise InvocationError("No frame available")

        # Create Blob using from_bytes class method (required for Pydantic 2.x)
        return JPEGBlob.from_bytes(frame)

    @lt_action
    def set_resolution(
        self, preset: Optional[str] = None, width: Optional[int] = None, height: Optional[int] = None
    ) -> dict:
        """Set camera resolution.

        Args:
            preset: Resolution preset name (optional)
            width: Resolution width in pixels (optional)
            height: Resolution height in pixels (optional)

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        params: dict[str, Any] = {}
        if preset:
            params["preset"] = preset
        if width and height:
            params["width"] = int(width)
            params["height"] = int(height)

        self._camera.on_cam({"cmd": CMD_SET_RESOLUTION, "parameters": params})
        return {"ok": True}

    @lt_action
    def set_snapshot_resolution(
        self, mode: str, width: Optional[int] = None, height: Optional[int] = None
    ) -> dict:
        """Set snapshot resolution mode.

        Args:
            mode: Snapshot mode ("display", "full", or "custom")
            width: Resolution width in pixels (required for custom mode)
            height: Resolution height in pixels (required for custom mode)

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        params: dict[str, Any] = {"mode": mode}
        if width and height:
            params["width"] = int(width)
            params["height"] = int(height)

        self._camera.on_cam({"cmd": CMD_SET_SNAPSHOT_RESOLUTION, "parameters": params})
        return {"ok": True}

    @lt_action
    def set_roi(self, x: int, y: int, w: int, h: int) -> dict:
        """Set region of interest (ROI) for camera.

        Args:
            x: ROI x coordinate
            y: ROI y coordinate
            w: ROI width
            h: ROI height

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        self._camera.on_roi({"cmd": CMD_SET, "parameters": {"x": x, "y": y, "w": w, "h": h}})
        return {"ok": True}

    @lt_action
    def clear_roi(self) -> dict:
        """Clear region of interest (ROI).

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        self._camera.on_roi({"cmd": CMD_CLEAR, "parameters": {}})
        return {"ok": True}

    @lt_action
    def record_roi_frames(self, frames: int) -> dict:
        """Record a fixed number of ROI frames as JPEGs.

        Args:
            frames: Number of ROI frames to save

        Returns:
            Dict with status, counts, and output folder

        Raises:
            InvocationError: If camera unavailable or recording failed
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        result = self._camera.record_roi_frames(int(frames))
        if not result.get("ok"):
            raise InvocationError(result.get("error") or "ROI recording failed")
        return result

    @lt_action
    def strobe_enable(self, on: bool) -> dict:
        """Enable or disable strobe.

        Args:
            on: True to enable, False to disable

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        self._camera.on_strobe({"cmd": CMD_ENABLE, "parameters": {"on": 1 if on else 0}})
        return {"ok": True}

    @lt_action
    def strobe_hold(self, on: bool) -> dict:
        """Enable or disable strobe hold mode.

        Args:
            on: True to enable hold, False to disable

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        self._camera.on_strobe({"cmd": CMD_HOLD, "parameters": {"on": 1 if on else 0}})
        return {"ok": True}

    @lt_action
    def strobe_timing(self, period_ns: int, wait_ns: Optional[int] = None) -> dict:
        """Set strobe timing parameters.

        Args:
            period_ns: Strobe period in nanoseconds
            wait_ns: Wait time in nanoseconds (optional)

        Returns:
            {"ok": True} on success

        Raises:
            InvocationError: If camera unavailable
        """
        if self._camera is None:
            raise InvocationError("Camera unavailable")

        params = {"period_ns": int(period_ns)}
        if wait_ns is not None:
            params["wait_ns"] = int(wait_ns)

        self._camera.on_strobe({"cmd": CMD_TIMING, "parameters": params})
        return {"ok": True}
