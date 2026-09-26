from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str


class SafeSystemController:
    """Allowlisted operating-system controls. There is intentionally no command runner."""

    ALLOWED = frozenset({
        "set_volume", "mute", "media_play_pause", "media_next", "media_previous",
        "screenshot", "open_folder", "system_info", "launch_app",
    })

    # Only these specific executables can be launched — no arbitrary paths
    LAUNCHABLE_APPS: dict[str, str] = {
        "calculator": "calc.exe",
        "notepad":    "notepad.exe",
        "explorer":   "explorer.exe",
        "taskmanager": "taskmgr.exe",
    }

    def __init__(self, allowed_folders: list[Path] | None = None) -> None:
        self.allowed_folders = [
            folder.resolve()
            for folder in (allowed_folders or [Path.home() / "Documents", Path.home() / "Desktop"])
            if folder.exists()
        ]
        self._volume: float | None = None
        self._endpoint = None
        self.audio_error: str | None = None
        self._vk_available = False
        self._initialize_audio()
        self._initialize_media_keys()

    def _initialize_audio(self) -> None:
        if platform.system() != "Windows":
            self.audio_error = "System volume control is implemented for Windows only."
            return
        try:
            from pycaw.pycaw import AudioUtilities
            device = AudioUtilities.GetSpeakers()
            self._endpoint = getattr(device, "EndpointVolume", getattr(device, "_volume", None))
            if self._endpoint is None:
                raise RuntimeError("No master-volume endpoint")
            self._volume = float(self._endpoint.GetMasterVolumeLevelScalar())
        except Exception as exc:
            self.audio_error = f"Audio control unavailable: {exc}"

    def _initialize_media_keys(self) -> None:
        """Check if we can simulate media key presses via ctypes on Windows."""
        if platform.system() != "Windows":
            return
        try:
            import ctypes  # noqa: F401
            self._vk_available = True
        except Exception:
            pass

    def validate(self, action: str) -> bool:
        return action in self.ALLOWED

    def execute(self, action: str, **parameters) -> ActionResult:
        if not self.validate(action):
            return ActionResult(False, f"Blocked non-allowlisted action: {action}")
        methods: dict[str, Callable[..., ActionResult]] = {
            "set_volume":       self.set_volume,
            "mute":             self.mute,
            "screenshot":       self.screenshot,
            "open_folder":      self.open_folder,
            "system_info":      self.system_info,
            "launch_app":       self.launch_app,
            "media_play_pause": self.media_play_pause,
            "media_next":       self.media_next,
            "media_previous":   self.media_previous,
        }
        return methods[action](**parameters)

    # --- Audio ---

    def set_volume(self, value: float) -> ActionResult:
        if self._endpoint is None:
            return ActionResult(False, self.audio_error or "Audio endpoint unavailable.")
        value = max(0.0, min(1.0, float(value)))
        try:
            self._endpoint.SetMasterVolumeLevelScalar(value, None)
            self._volume = value
            return ActionResult(True, f"System volume set to {round(value * 100)}%.")
        except Exception as exc:
            return ActionResult(False, f"Could not set system volume: {exc}")

    def mute(self, muted: bool = True) -> ActionResult:
        if self._endpoint is None:
            return ActionResult(False, self.audio_error or "Audio endpoint unavailable.")
        try:
            self._endpoint.SetMute(int(muted), None)
            return ActionResult(True, "System muted." if muted else "System unmuted.")
        except Exception as exc:
            return ActionResult(False, f"Could not change mute state: {exc}")

    # --- Media transport ---

    def media_play_pause(self) -> ActionResult:
        return self._send_media_key(0xB3, "Play/Pause")

    def media_next(self) -> ActionResult:
        return self._send_media_key(0xB0, "Next Track")

    def media_previous(self) -> ActionResult:
        return self._send_media_key(0xB1, "Previous Track")

    def _send_media_key(self, vk_code: int, label: str) -> ActionResult:
        if not self._vk_available:
            return ActionResult(False, f"{label}: media key simulation unavailable.")
        try:
            import ctypes
            KEYEVENTF_EXTENDEDKEY = 0x0001
            KEYEVENTF_KEYUP = 0x0002
            user32 = ctypes.windll.user32
            user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            return ActionResult(True, f"{label} key sent.")
        except Exception as exc:
            return ActionResult(False, f"{label} failed: {exc}")

    # --- Screenshot ---

    def screenshot(self, destination: Path | None = None) -> ActionResult:
        try:
            from PIL import ImageGrab
            if destination is None:
                from datetime import datetime
                destination = Path("captures") / f"screenshot-{datetime.now():%Y%m%d-%H%M%S}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            ImageGrab.grab().save(destination)
            return ActionResult(True, f"Screenshot saved to {destination}")
        except Exception as exc:
            return ActionResult(False, f"Screenshot unavailable: {exc}")

    # --- File system ---

    def open_folder(self, folder: Path) -> ActionResult:
        try:
            resolved = folder.resolve()
            if not any(resolved == permitted or permitted in resolved.parents for permitted in self.allowed_folders):
                return ActionResult(False, "Blocked folder outside configured allowlist.")
            os.startfile(resolved)  # type: ignore[attr-defined]
            return ActionResult(True, f"Opened {resolved}")
        except Exception as exc:
            return ActionResult(False, f"Could not open folder: {exc}")

    # --- App launcher (allowlisted only) ---

    def launch_app(self, app_name: str) -> ActionResult:
        executable = self.LAUNCHABLE_APPS.get(app_name.lower())
        if executable is None:
            return ActionResult(False, f"Application '{app_name}' is not in the launch allowlist.")
        try:
            os.startfile(executable)  # type: ignore[attr-defined]
            return ActionResult(True, f"Launched {app_name}.")
        except Exception as exc:
            return ActionResult(False, f"Could not launch {app_name}: {exc}")

    # --- System info ---

    @staticmethod
    def system_info() -> ActionResult:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        info = (
            f"{platform.system()} {platform.release()} | {platform.machine()} | "
            f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024**3)}/{mem.total // (1024**3)} GB)"
        )
        return ActionResult(True, info)
