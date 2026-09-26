from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass
class FramePacket:
    image: Any
    timestamp: float
    fps: float
    frame_latency_ms: float
    dropped_frames: int


class Camera:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720) -> None:
        self.index, self.width, self.height = index, width, height
        self.capture: Any | None = None
        self._last_timestamp: float | None = None
        self._dropped_frames = 0
        self.error: str | None = None

    def start(self) -> bool:
        try:
            import cv2
            backend = getattr(cv2, "CAP_DSHOW", 0)
            self.capture = cv2.VideoCapture(self.index, backend)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.capture.isOpened():
                self.error = f"Camera {self.index} could not be opened. Check camera permissions or index."
                self.release()
                return False
            return True
        except Exception as exc:
            self.error = f"Camera initialization failed: {exc}"
            self.release()
            return False

    def read(self) -> FramePacket | None:
        if self.capture is None:
            return None
        started = perf_counter()
        ok, frame = self.capture.read()
        now = perf_counter()
        if not ok or frame is None:
            self._dropped_frames += 1
            self.error = "Camera returned an empty frame."
            return None
        delta = now - self._last_timestamp if self._last_timestamp else 0.0
        self._last_timestamp = now
        fps = (1.0 / delta) if delta else 0.0
        return FramePacket(frame, now, fps, (now - started) * 1000.0, self._dropped_frames)

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
        self.capture = None
