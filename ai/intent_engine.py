from __future__ import annotations

from dataclasses import dataclass

from core.models import GestureEvent, GestureName, GestureState, Intent


@dataclass(frozen=True)
class VoiceCommand:
    text: str
    confidence: float = 0.75


class IntentEngine:
    """Deterministic multimodal resolver; a local LLM can only suggest this vocabulary."""

    MODULES = ("home", "music", "camera", "system", "files", "projects", "ai assistant", "3d space", "settings")

    # Comprehensive voice-to-intent map
    VOICE_MAP: dict[str, tuple[str, str | None, dict]] = {
        # Navigation
        "go home":                  ("open_module",      "home",         {}),
        "open home":                ("open_module",      "home",         {}),
        "open music":               ("open_module",      "music",        {}),
        "open the music interface": ("open_module",      "music",        {}),
        "open camera":              ("open_module",      "camera",       {}),
        "open projects":            ("open_module",      "projects",     {}),
        "open system":              ("open_module",      "system",       {}),
        "open files":               ("open_module",      "files",        {}),
        "open settings":            ("open_module",      "settings",     {}),
        "activate ai":              ("open_module",      "ai assistant", {}),
        "open the 3d environment":  ("open_module",      "3d space",     {}),
        "switch to 3d mode":        ("open_module",      "3d space",     {}),
        # Media
        "play music":               ("media_play_pause", None,           {}),
        "pause music":              ("media_play_pause", None,           {}),
        "next song":                ("media_next",       None,           {}),
        "next track":               ("media_next",       None,           {}),
        "previous song":            ("media_previous",   None,           {}),
        "previous track":           ("media_previous",   None,           {}),
        # Volume
        "turn volume up":           ("adjust_volume",    None,           {"direction": "up"}),
        "turn volume down":         ("adjust_volume",    None,           {"direction": "down"}),
        "increase volume":          ("adjust_volume",    None,           {"direction": "up"}),
        "decrease volume":          ("adjust_volume",    None,           {"direction": "down"}),
        "mute":                     ("mute",             None,           {}),
        # Camera
        "take a picture":           ("capture_photo",    "camera",       {}),
        "take photo":               ("capture_photo",    "camera",       {}),
        "take a photo":             ("capture_photo",    "camera",       {}),
        # System
        "show system information":  ("open_module",      "system",       {}),
        "show system status":       ("open_module",      "system",       {}),
        "system info":              ("system_info",      None,           {}),
        # Screenshot
        "take screenshot":          ("screenshot",       None,           {}),
    }

    # Volume phrases that include an explicit numeric value
    VOLUME_PATTERN_KEYWORDS = ("set volume to", "volume to", "volume at")

    # Context-aware gesture → action routing per active module
    CONTEXT_GESTURE_MAP: dict[str, dict[GestureName, str]] = {
        "music": {
            GestureName.SWIPE_LEFT:  "media_previous",
            GestureName.SWIPE_RIGHT: "media_next",
            GestureName.OPEN_PALM:   "media_play_pause",
            GestureName.THUMB_UP:    "adjust_volume_up",
            GestureName.THUMB_DOWN:  "adjust_volume_down",
        },
        "camera": {
            GestureName.PINCH:       "capture_photo",
            GestureName.THUMB_UP:    "confirm",
        },
        "3d space": {
            GestureName.SWIPE_LEFT:  "rotate_left",
            GestureName.SWIPE_RIGHT: "rotate_right",
            GestureName.SWIPE_UP:    "rotate_up",
            GestureName.SWIPE_DOWN:  "rotate_down",
            GestureName.PINCH:       "select_3d",
            GestureName.OPEN_PALM:   "reset_view",
        },
        "home": {
            GestureName.SWIPE_LEFT:  "previous_module",
            GestureName.SWIPE_RIGHT: "next_module",
        },
    }

    def resolve(
        self,
        voice: VoiceCommand | None,
        gesture: GestureEvent | None,
        active_module: str,
        pointed_target: str | None = None,
    ) -> Intent | None:
        modalities: list[str] = []

        # --- VOICE RESOLUTION ---
        if voice:
            normalized = voice.text.strip().lower().rstrip(".!")

            # Check explicit volume-set pattern: "set volume to 50 percent"
            volume_intent = self._parse_volume_command(normalized)
            if volume_intent is not None:
                modalities.append("voice")
                return Intent("set_volume", None, voice.confidence, tuple(modalities),
                              parameters={"value": volume_intent})

            # Check static voice map
            match = self.VOICE_MAP.get(normalized)
            if match:
                action, target, params = match
                if action == "open_module" and pointed_target in self.MODULES:
                    target = pointed_target
                    modalities.append("gesture")
                modalities.insert(0, "voice")
                conf = min(0.99, voice.confidence + (0.12 if pointed_target else 0))
                return Intent(action, target, conf, tuple(modalities), parameters=dict(params))

        # --- GESTURE RESOLUTION ---
        if gesture is None:
            return None

        # Only act on START for discrete gestures (prevent repeated triggers)
        if gesture.state != GestureState.START:
            if gesture.state == GestureState.HOLD and gesture.gesture == GestureName.POINT:
                return Intent("select", pointed_target, gesture.confidence, ("gesture",))
            return None

        # Context-aware gesture mapping
        context_map = self.CONTEXT_GESTURE_MAP.get(active_module, {})
        context_action = context_map.get(gesture.gesture)

        if context_action:
            return Intent(context_action, pointed_target or active_module,
                          gesture.confidence, ("gesture",))

        # Default gesture actions (module-independent)
        if gesture.gesture == GestureName.PINCH:
            return Intent("activate", pointed_target or active_module,
                          gesture.confidence, ("gesture",))
        if gesture.gesture == GestureName.OPEN_PALM:
            return Intent("open_module", "home", gesture.confidence, ("gesture",))
        if gesture.gesture == GestureName.SWIPE_LEFT:
            return Intent("previous_module", None, gesture.confidence, ("gesture",))
        if gesture.gesture == GestureName.SWIPE_RIGHT:
            return Intent("next_module", None, gesture.confidence, ("gesture",))
        if gesture.gesture == GestureName.POINT:
            return Intent("select", pointed_target, gesture.confidence, ("gesture",))
        if gesture.gesture == GestureName.THUMB_UP:
            return Intent("confirm", pointed_target, gesture.confidence, ("gesture",))
        if gesture.gesture == GestureName.THUMB_DOWN:
            return Intent("cancel", pointed_target, gesture.confidence, ("gesture",))

        return None

    @staticmethod
    def _parse_volume_command(text: str) -> float | None:
        """Extract a numeric volume value from natural-language commands."""
        import re
        for prefix in IntentEngine.VOLUME_PATTERN_KEYWORDS:
            if text.startswith(prefix):
                remainder = text[len(prefix):].strip()
                match = re.match(r"(\d+)", remainder)
                if match:
                    return max(0.0, min(1.0, int(match.group(1)) / 100.0))
        return None
