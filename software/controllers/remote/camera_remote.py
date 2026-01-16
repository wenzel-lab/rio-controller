"""Remote camera controller adapter (API-backed)."""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from PIL import Image

from client import RioClient, RioAPIError
from config import (
    CAMERA_THREAD_WIDTH,
    CAMERA_THREAD_HEIGHT,
    SNAPSHOT_FOLDER,
    SNAPSHOT_FILENAME_PREFIX,
    SNAPSHOT_FILENAME_SUFFIX,
    SNAPSHOT_RESOLUTION_DISPLAY,
    CAMERA_SNAPSHOT_JPEG_QUALITY,
    WS_EVENT_CAM,
    WS_EVENT_STROBE,
    WS_EVENT_ROI,
    CMD_SNAPSHOT,
    CMD_SET_RESOLUTION,
    CMD_SET_SNAPSHOT_RESOLUTION,
    CMD_SET,
    CMD_GET,
    CMD_CLEAR,
    CMD_ENABLE,
    CMD_HOLD,
    CMD_TIMING,
)

logger = logging.getLogger(__name__)


class _RemoteThread:
    def is_alive(self) -> bool:
        return True

    def join(self, timeout: Optional[float] = None) -> None:
        return None


class _RemoteStrobeCam:
    def __init__(self, client: RioClient, camera: "RemoteCamera") -> None:
        self._client = client
        self._camera = camera

    def set_camera_type(self, camera_type: str) -> bool:
        try:
            self._client.set_camera_type(camera_type)
            self._camera.update_camera_data()
            return True
        except RioAPIError as exc:
            logger.warning("Remote camera select failed: %s", exc)
            return False


class RemoteCamera:
    """API-backed adapter that mimics Camera for the Flask UI."""

    def __init__(self, exit_event: Any, socketio: Any, client: RioClient) -> None:
        self.exit_event = exit_event
        self.socketio = socketio
        self._client = client
        self.thread = _RemoteThread()
        self.is_remote = True

        self.cam_data: Dict[str, Any] = {"camera": "none", "status": ""}
        self.strobe_data: Dict[str, Any] = {
            "hold": 0,
            "enable": 0,
            "wait_ns": 0,
            "period_ns": 0,
            "framerate": 0,
            "cam_read_time_us": 0,
        }
        self.display_resolution: Tuple[int, int] = (CAMERA_THREAD_WIDTH, CAMERA_THREAD_HEIGHT)
        self.snapshot_resolution_mode: str = SNAPSHOT_RESOLUTION_DISPLAY
        self.snapshot_resolution: Optional[Tuple[int, int]] = None
        self.roi: Optional[Dict[str, int]] = None

        self.strobe_cam = _RemoteStrobeCam(client, self)
        self._register_websocket_handlers()
        self.update_camera_data()
        self.update_strobe_data()

    def _register_websocket_handlers(self) -> None:
        if self.socketio is None:
            logger.warning("RemoteCamera cannot register WebSocket handlers (socketio is None)")
            return

        @self.socketio.on(WS_EVENT_CAM)
        def on_cam(data: Dict[str, Any]) -> None:
            self.on_cam(data)

        @self.socketio.on(WS_EVENT_STROBE)
        def on_strobe(data: Dict[str, Any]) -> None:
            self.on_strobe(data)

        @self.socketio.on(WS_EVENT_ROI)
        def on_roi(data: Dict[str, Any]) -> None:
            self.on_roi(data)

    def initialize(self) -> None:
        """Remote camera does not need local initialization."""
        return None

    def update_camera_data(self) -> None:
        try:
            state = self._client.get_camera_state()
            self.cam_data["camera"] = state.get("camera", self.cam_data.get("camera", "none"))
            self.cam_data["status"] = state.get("status", self.cam_data.get("status", ""))
            display_width = state.get("display_width")
            display_height = state.get("display_height")
            if display_width and display_height:
                self.display_resolution = (int(display_width), int(display_height))
                self.cam_data["display_width"] = int(display_width)
                self.cam_data["display_height"] = int(display_height)
            self.snapshot_resolution_mode = state.get(
                "snapshot_resolution_mode", self.snapshot_resolution_mode
            )
            self.cam_data["snapshot_resolution_mode"] = self.snapshot_resolution_mode
            snapshot_width = state.get("snapshot_width")
            snapshot_height = state.get("snapshot_height")
            if snapshot_width and snapshot_height:
                self.snapshot_resolution = (int(snapshot_width), int(snapshot_height))
                self.cam_data["snapshot_width"] = int(snapshot_width)
                self.cam_data["snapshot_height"] = int(snapshot_height)
            self.roi = state.get("roi") or None
        except RioAPIError as exc:
            logger.warning("Remote camera state fetch failed: %s", exc)

    def update_strobe_data(self) -> None:
        try:
            state = self._client.get_strobe_state()
            self.strobe_data.update(state)
        except RioAPIError as exc:
            logger.warning("Remote strobe state fetch failed: %s", exc)

    def get_frame(self) -> Optional[bytes]:
        try:
            return self._client.get_camera_snapshot()
        except RioAPIError as exc:
            logger.warning("Remote snapshot failed: %s", exc)
            return None

    def save(self) -> None:
        frame_data = self.get_frame()
        if not frame_data:
            logger.warning("Remote snapshot unavailable")
            return
        try:
            import os

            os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)
            img = Image.open(io.BytesIO(frame_data))
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{SNAPSHOT_FILENAME_PREFIX}{current_time}{SNAPSHOT_FILENAME_SUFFIX}"
            filepath = f"{SNAPSHOT_FOLDER}/{filename}"
            img.save(filepath, "JPEG", quality=CAMERA_SNAPSHOT_JPEG_QUALITY)
            logger.info("Remote snapshot saved: %s", filepath)
        except Exception as exc:
            logger.error("Remote snapshot save failed: %s", exc)

    def on_cam(self, data: Dict[str, Any]) -> None:
        cmd = data.get("cmd")
        if cmd == CMD_SNAPSHOT:
            self.save()
        elif cmd == CMD_SET_RESOLUTION:
            params = data.get("parameters", {})
            try:
                self._client.set_camera_resolution(
                    preset=params.get("preset"),
                    width=params.get("width"),
                    height=params.get("height"),
                )
            except RioAPIError as exc:
                logger.warning("Remote set_resolution failed: %s", exc)
        elif cmd == CMD_SET_SNAPSHOT_RESOLUTION:
            params = data.get("parameters", {})
            try:
                self._client.set_camera_snapshot_resolution(
                    mode=params.get("mode", SNAPSHOT_RESOLUTION_DISPLAY),
                    width=params.get("width"),
                    height=params.get("height"),
                )
            except RioAPIError as exc:
                logger.warning("Remote set_snapshot_resolution failed: %s", exc)
        else:
            logger.warning("Remote camera command not supported: %s", cmd)

        self.update_camera_data()
        self.update_strobe_data()
        if self.socketio:
            self.socketio.emit(WS_EVENT_STROBE, self.strobe_data)
            self.socketio.emit(WS_EVENT_CAM, self.cam_data)

    def on_strobe(self, data: Dict[str, Any]) -> None:
        cmd = data.get("cmd")
        params = data.get("parameters", {})
        try:
            if cmd == CMD_HOLD:
                self._client.set_strobe_hold(bool(params.get("on", 0)))
            elif cmd == CMD_ENABLE:
                self._client.set_strobe_enable(bool(params.get("on", 0)))
            elif cmd == CMD_TIMING:
                period_ns = int(params.get("period_ns", 0))
                wait_ns = params.get("wait_ns")
                self._client.set_strobe_timing(period_ns, wait_ns=wait_ns)
            else:
                logger.warning("Remote strobe command not supported: %s", cmd)
        except RioAPIError as exc:
            logger.warning("Remote strobe command failed: %s", exc)

        self.update_strobe_data()
        if self.socketio:
            self.socketio.emit(WS_EVENT_STROBE, self.strobe_data)

    def on_roi(self, data: Dict[str, Any]) -> None:
        cmd = data.get("cmd")
        params = data.get("parameters", {})
        try:
            if cmd == CMD_SET:
                self._client.set_camera_roi(
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    int(params.get("w", 0)),
                    int(params.get("h", 0)),
                )
            elif cmd == CMD_CLEAR:
                self._client.clear_camera_roi()
            elif cmd != CMD_GET:
                logger.warning("Remote ROI command not supported: %s", cmd)
        except RioAPIError as exc:
            logger.warning("Remote ROI command failed: %s", exc)

        self.update_camera_data()
        if self.socketio:
            self.socketio.emit(WS_EVENT_ROI, self.roi or {})

    def get_roi(self) -> Optional[Tuple[int, int, int, int]]:
        if not self.roi:
            return None
        return (self.roi["x"], self.roi["y"], self.roi["w"], self.roi["h"])
