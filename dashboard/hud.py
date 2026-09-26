from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin


@dataclass
class DashboardState:
    module: str = "home"
    selected_module: str | None = None
    message: str = "SYSTEM ONLINE"
    gesture: str = "NONE"
    confidence: float = 0.0
    fps: float = 0.0
    latency_ms: float = 0.0
    voice_status: str = "OFFLINE"
    ai_status: str = "OPTIONAL"
    camera_status: str = "ONLINE"
    hand_mode: str = "ONE_HAND_MODE"
    volume: float | None = None


class CyberneticDashboard:
    MODULES = ("home", "music", "camera", "system", "files", "projects", "ai assistant", "3d space", "settings")

    def __init__(self) -> None:
        self.state = DashboardState()

    def next_module(self, step: int = 1) -> str:
        index = self.MODULES.index(self.state.module)
        self.state.module = self.MODULES[(index + step) % len(self.MODULES)]
        self.state.selected_module = self.state.module
        return self.state.module

    def select_from_point(self, point: tuple[int, int], frame_shape: tuple[int, int]) -> str | None:
        height, width = frame_shape[:2]
        cards = self._module_rectangles(width, height)
        for module, (x1, y1, x2, y2) in cards.items():
            if x1 <= point[0] <= x2 and y1 <= point[1] <= y2:
                self.state.selected_module = module
                return module
        return None

    def render(self, frame):
        import cv2
        import numpy as np

        height, width = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, height), (10, 12, 18), -1)
        cv2.addWeighted(overlay, 0.56, frame, 0.44, 0, frame)
        self._top_bar(frame, width)
        self._module_surface(frame, width, height)
        self._status_rail(frame, width, height)
        self._hand_hud(frame, width, height)
        return frame

    def _top_bar(self, frame, width: int) -> None:
        import cv2
        cv2.rectangle(frame, (20, 18), (width - 20, 76), (18, 28, 34), -1)
        cv2.line(frame, (20, 76), (width - 20, 76), (76, 212, 196), 1)
        cv2.putText(frame, "CYBERNETIC OS", (38, 53), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (230, 245, 240), 2)
        text = f"MODE: {self.state.module.upper()}"
        cv2.putText(frame, text, (width - 330, 53), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (130, 220, 210), 1)

    def _module_surface(self, frame, width: int, height: int) -> None:
        import cv2
        cv2.putText(frame, self.state.module.upper(), (42, 126), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (250, 185, 90), 2)
        cv2.putText(frame, self.state.message[:68], (42, 154), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (215, 225, 225), 1)
        cards = self._module_rectangles(width, height)
        for module, (x1, y1, x2, y2) in cards.items():
            selected = module == self.state.selected_module or module == self.state.module
            fill = (36, 54, 58) if selected else (24, 31, 38)
            accent = (76, 212, 196) if selected else (74, 94, 101)
            cv2.rectangle(frame, (x1, y1), (x2, y2), fill, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), accent, 1)
            label = module.upper()
            cv2.putText(frame, label, (x1 + 14, y1 + 31), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (236, 244, 240), 1)
            status = self._module_status(module)
            cv2.putText(frame, status, (x1 + 14, y1 + 54), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (154, 179, 178), 1)

    def _status_rail(self, frame, width: int, height: int) -> None:
        import cv2
        x1, x2 = width - 265, width - 22
        y1 = 180
        cv2.rectangle(frame, (x1, y1), (x2, height - 24), (14, 22, 29), -1)
        cv2.rectangle(frame, (x1, y1), (x2, height - 24), (73, 107, 111), 1)
        rows = [
            ("GESTURE", self.state.gesture),
            ("CONFIDENCE", f"{self.state.confidence:.0%}"),
            ("FPS", f"{self.state.fps:.1f}" if self.state.fps else "MEASURING"),
            ("LATENCY", f"{self.state.latency_ms:.1f} ms"),
            ("CAMERA", self.state.camera_status),
            ("VOICE", self.state.voice_status.split(" ")[0]),
            ("AI", self.state.ai_status),
            ("HANDS", self.state.hand_mode),
        ]
        if self.state.volume is not None:
            rows.append(("VOLUME", f"{self.state.volume:.0%}"))
        y = y1 + 28
        for label, value in rows:
            cv2.putText(frame, label, (x1 + 15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (114, 154, 157), 1)
            cv2.putText(frame, value[:24], (x1 + 15, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (220, 236, 232), 1)
            y += 47

    def _hand_hud(self, frame, width: int, height: int) -> None:
        import cv2
        center = (width - 145, 122)
        for radius, color in ((42, (73, 204, 191)), (31, (56, 137, 139)), (20, (247, 177, 84))):
            cv2.circle(frame, center, radius, color, 1)
        for index in range(12):
            angle = index * pi / 6
            start = (int(center[0] + 45 * cos(angle)), int(center[1] + 45 * sin(angle)))
            end = (int(center[0] + 50 * cos(angle)), int(center[1] + 50 * sin(angle)))
            cv2.line(frame, start, end, (73, 204, 191), 1)
        cv2.putText(frame, "INPUT", (width - 172, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (156, 200, 197), 1)

    def _module_rectangles(self, width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
        rail_start = width - 290
        usable_width = max(360, rail_start - 44)
        x, y = 42, 184
        gap, card_w, card_h = 12, max(120, (usable_width - 24) // 3), 76
        cards: dict[str, tuple[int, int, int, int]] = {}
        for index, module in enumerate(self.MODULES):
            col, row = index % 3, index // 3
            x1, y1 = x + col * (card_w + gap), y + row * (card_h + gap)
            cards[module] = (x1, y1, x1 + card_w, y1 + card_h)
        return cards

    @staticmethod
    def _module_status(module: str) -> str:
        return {
            "home": "navigation hub", "music": "media commands", "camera": "pinch to capture",
            "system": "safe controls", "files": "trusted folders", "projects": "workspace view",
            "ai assistant": "local optional", "3d space": "WebGL interaction", "settings": "calibration",
        }[module]
