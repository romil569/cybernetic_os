from __future__ import annotations

import ctypes
from dataclasses import dataclass


@dataclass
class SpatialCursor:
    sensitivity: float = 1.0
    enabled: bool = False
    _position: tuple[float, float] | None = None

    def update(self, normalized: tuple[float, float]) -> tuple[int, int] | None:
        """Maps a hand coordinate to a smoothed Windows cursor only when explicitly enabled."""
        if not self.enabled:
            return None
        user32 = ctypes.windll.user32
        width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        x = max(0.02, min(0.98, normalized[0])) * width
        y = max(0.02, min(0.98, normalized[1])) * height
        if self._position is not None:
            x = self._position[0] * 0.72 + x * 0.28
            y = self._position[1] * 0.72 + y * 0.28
        self._position = (x, y)
        user32.SetCursorPos(int(x), int(y))
        return int(x), int(y)

    def click(self) -> None:
        if self.enabled:
            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
