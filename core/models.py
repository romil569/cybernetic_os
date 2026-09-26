from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GestureName(str, Enum):
    NONE = "NONE"
    OPEN_PALM = "OPEN_PALM"
    FIST = "FIST"
    POINT = "POINT"
    PINCH = "PINCH"
    TWO_FINGER = "TWO_FINGER"
    THUMB_UP = "THUMB_UP"
    THUMB_DOWN = "THUMB_DOWN"
    SWIPE_LEFT = "SWIPE_LEFT"
    SWIPE_RIGHT = "SWIPE_RIGHT"
    SWIPE_UP = "SWIPE_UP"
    SWIPE_DOWN = "SWIPE_DOWN"


class GestureState(str, Enum):
    START = "START"
    HOLD = "HOLD"
    RELEASE = "RELEASE"
    IDLE = "IDLE"


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0


@dataclass
class HandSnapshot:
    landmarks: list[Landmark]
    handedness: str
    confidence: float
    palm: tuple[float, float]
    fingertip_pixels: dict[str, tuple[int, int]]
    velocity: tuple[float, float] = (0.0, 0.0)
    timestamp: float = 0.0

    @property
    def index_tip(self) -> Landmark:
        return self.landmarks[8]


@dataclass(frozen=True)
class GestureEvent:
    gesture: GestureName
    state: GestureState
    confidence: float
    timestamp: float
    velocity: tuple[float, float] = (0.0, 0.0)


@dataclass(frozen=True)
class Intent:
    name: str
    target: str | None
    confidence: float
    modalities: tuple[str, ...]
    parameters: dict[str, Any] = field(default_factory=dict)
