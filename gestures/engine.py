from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from math import hypot
from time import monotonic

from core.models import GestureEvent, GestureName, GestureState, HandSnapshot, Landmark
from vision.hand_tracker import distance


@dataclass
class GestureEngineConfig:
    smoothing_frames: int = 4
    cooldown_seconds: float = 0.55
    swipe_velocity: float = 0.70
    pinch_ratio: float = 0.48


class GestureEngine:
    """Classifies normalized landmarks and emits debounced temporal gesture events."""

    def __init__(self, config: GestureEngineConfig | None = None) -> None:
        self.config = config or GestureEngineConfig()
        self._recent: deque[GestureName] = deque(maxlen=self.config.smoothing_frames)
        self._active = GestureName.NONE
        self._last_emit: dict[GestureName, float] = {}

    def classify(self, hand: HandSnapshot) -> tuple[GestureName, float]:
        if len(hand.landmarks) < 21:
            return GestureName.NONE, 0.0
        lm = hand.landmarks
        palm_size = max(distance(lm[0], lm[9]), 0.02)
        pinch = distance(lm[4], lm[8]) / palm_size
        extended = [self._extended(lm, tip, pip) for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18))]
        count = sum(extended)
        vx, vy = hand.velocity
        speed = hypot(vx, vy)
        if pinch <= self.config.pinch_ratio:
            return GestureName.PINCH, min(1.0, 1.0 - pinch / self.config.pinch_ratio)
        if speed >= self.config.swipe_velocity and count >= 1:
            if abs(vx) > abs(vy):
                return (GestureName.SWIPE_RIGHT if vx > 0 else GestureName.SWIPE_LEFT), min(1.0, speed / 2)
            return (GestureName.SWIPE_DOWN if vy > 0 else GestureName.SWIPE_UP), min(1.0, speed / 2)
        if count == 4:
            return GestureName.OPEN_PALM, 0.9
        if count == 0:
            thumb_up = lm[4].y < lm[3].y
            thumb_down = lm[4].y > lm[3].y
            if thumb_up:
                return GestureName.THUMB_UP, 0.7
            if thumb_down:
                return GestureName.THUMB_DOWN, 0.7
            return GestureName.FIST, 0.9
        if extended[0] and not any(extended[1:]):
            return GestureName.POINT, 0.9
        if extended[0] and extended[1] and not any(extended[2:]):
            return GestureName.TWO_FINGER, 0.85
        return GestureName.NONE, 0.0

    def update(self, hand: HandSnapshot | None, now: float | None = None) -> GestureEvent | None:
        now = monotonic() if now is None else now
        raw, confidence = self.classify(hand) if hand is not None else (GestureName.NONE, 0.0)
        self._recent.append(raw)
        stable = Counter(self._recent).most_common(1)[0][0] if self._recent else GestureName.NONE
        if stable == GestureName.NONE and self._active != GestureName.NONE:
            previous, self._active = self._active, GestureName.NONE
            return GestureEvent(previous, GestureState.RELEASE, 1.0, now)
        if stable == GestureName.NONE:
            return None
        if stable != self._active:
            if now - self._last_emit.get(stable, -999.0) < self.config.cooldown_seconds:
                return None
            self._active = stable
            self._last_emit[stable] = now
            return GestureEvent(stable, GestureState.START, confidence, now, hand.velocity if hand else (0, 0))
        return GestureEvent(stable, GestureState.HOLD, confidence, now, hand.velocity if hand else (0, 0))

    @staticmethod
    def _extended(lm: list[Landmark], tip: int, pip: int) -> bool:
        return lm[tip].y < lm[pip].y - 0.015
