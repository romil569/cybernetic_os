from __future__ import annotations

from collections import deque
from math import hypot
from time import perf_counter

from core.models import HandSnapshot, Landmark


class HandTracker:
    """MediaPipe adapter that deliberately degrades to no-hands when unavailable."""

    def __init__(self, max_hands: int = 2, smoothing: float = 0.45,
                 min_detection: float = 0.65, min_tracking: float = 0.65) -> None:
        self.available = False
        self.error: str | None = None
        self._hands = None
        self._draw = None
        self._connections = None
        self._history: dict[str, deque[tuple[float, float, float]]] = {}
        self.smoothing = smoothing
        try:
            import mediapipe as mp
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=max_hands,
                min_detection_confidence=min_detection, min_tracking_confidence=min_tracking,
            )
            self._draw = mp.solutions.drawing_utils
            self._connections = mp.solutions.hands.HAND_CONNECTIONS
            self.available = True
        except Exception as exc:
            self.error = f"MediaPipe unavailable: {exc}"

    def process(self, frame, draw: bool = True) -> tuple[list[HandSnapshot], float]:
        if not self.available or self._hands is None:
            return [], 0.0
        import cv2
        started = perf_counter()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)
        elapsed_ms = (perf_counter() - started) * 1000.0
        if not result.multi_hand_landmarks:
            return [], elapsed_ms
        height, width = frame.shape[:2]
        output: list[HandSnapshot] = []
        handedness = result.multi_handedness or []
        for index, hand in enumerate(result.multi_hand_landmarks):
            label = handedness[index].classification[0].label if index < len(handedness) else "Unknown"
            confidence = float(handedness[index].classification[0].score) if index < len(handedness) else 0.5
            points = [Landmark(lm.x, lm.y, lm.z) for lm in hand.landmark]
            palm = ((points[0].x + points[5].x + points[17].x) / 3, (points[0].y + points[5].y + points[17].y) / 3)
            velocity = self._velocity(label, points[8].x, points[8].y)
            tips = {name: (int(points[i].x * width), int(points[i].y * height)) for name, i in
                    {"thumb": 4, "index": 8, "middle": 12, "ring": 16, "pinky": 20}.items()}
            output.append(HandSnapshot(points, label, confidence, palm, tips, velocity, perf_counter()))
            if draw and self._draw:
                self._draw.draw_landmarks(frame, hand, self._connections)
        return output, elapsed_ms

    def _velocity(self, label: str, x: float, y: float) -> tuple[float, float]:
        now = perf_counter()
        history = self._history.setdefault(label, deque(maxlen=3))
        if not history:
            history.append((x, y, now))
            return (0.0, 0.0)
        px, py, then = history[-1]
        history.append((x, y, now))
        dt = max(now - then, 0.001)
        return ((x - px) / dt, (y - py) / dt)

    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()


def distance(a: Landmark, b: Landmark) -> float:
    return hypot(a.x - b.x, a.y - b.y)
