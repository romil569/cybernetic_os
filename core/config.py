from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Settings:
    camera_index: int = 0
    width: int = 1280
    height: int = 720
    cursor_sensitivity: float = 1.0
    gesture_cooldown_seconds: float = 0.55
    enable_gaze: bool = False
    # Calibration thresholds
    pinch_threshold: float = 0.48
    swipe_sensitivity: float = 0.70
    smoothing_frames: int = 4
    confidence_threshold: float = 0.65
    gesture_bindings: dict[str, str] = field(default_factory=lambda: {
        "SWIPE_LEFT": "previous_module",
        "SWIPE_RIGHT": "next_module",
        "OPEN_PALM": "home",
        "PINCH_START": "activate",
    })


class ConfigStore:
    def __init__(self, root: Path) -> None:
        self.path = root / "config" / "settings.json"
        self.profile_path = root / "config" / "user_profile.json"

    def load(self) -> Settings:
        if not self.path.exists():
            settings = Settings()
            self.save(settings)
            return settings
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            # Only pass keys that Settings knows about (forward-compatible)
            known = {f.name for f in Settings.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known}
            return Settings(**filtered)
        except (json.JSONDecodeError, TypeError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")

    def load_profile(self) -> dict:
        if not self.profile_path.exists():
            return {"calibrated": False, "samples": {}}
        try:
            return json.loads(self.profile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"calibrated": False, "samples": {}}

    def save_profile(self, profile: dict) -> None:
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
