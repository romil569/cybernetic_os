from __future__ import annotations


class VoiceRecognizer:
    """Optional local Vosk integration boundary; never required by the camera loop."""

    def __init__(self) -> None:
        self.available = False
        self.status = "OFFLINE (install Vosk and a local model to enable voice)"
        try:
            import vosk  # noqa: F401
            self.status = "OFFLINE (no configured local Vosk model)"
        except ImportError:
            pass
