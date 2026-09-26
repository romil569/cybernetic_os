from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class MetricRecord:
    timestamp: str
    fps: float
    frame_latency_ms: float
    inference_ms: float
    dropped_frames: int
    gesture: str
    gesture_confidence: float


class Telemetry:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.recent_fps: deque[float] = deque(maxlen=240)
        self.recent_latency: deque[float] = deque(maxlen=240)

    def record(self, fps: float, frame_latency_ms: float, inference_ms: float, dropped_frames: int, gesture: str = "NONE", confidence: float = 0.0) -> None:
        self.recent_fps.append(fps)
        self.recent_latency.append(frame_latency_ms)
        record = MetricRecord(datetime.now(timezone.utc).isoformat(), fps, frame_latency_ms, inference_ms, dropped_frames, gesture, confidence)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(asdict(record)) + "\n")

    def summary(self) -> dict[str, float | str]:
        return {
            "avg_fps": sum(self.recent_fps) / len(self.recent_fps) if self.recent_fps else 0.0,
            "min_fps": min(self.recent_fps) if self.recent_fps else 0.0,
            "avg_latency_ms": sum(self.recent_latency) / len(self.recent_latency) if self.recent_latency else 0.0,
            "samples": float(len(self.recent_fps)),
        }
