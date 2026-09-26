"""Optional local Ollama adapter.

Converts natural-language text into a small, validated intent vocabulary.
The LLM may ONLY produce intents from the allowed set — it never receives
shell access, file-system write access, or any execution surface.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from core.models import Intent


ALLOWED_INTENTS: frozenset[str] = frozenset({
    "open_module", "activate", "capture_photo", "set_volume",
    "adjust_volume", "media_play_pause", "media_next", "media_previous",
    "mute", "system_info", "screenshot", "select", "next_module",
    "previous_module", "noop",
})

SYSTEM_PROMPT = (
    "You are a structured-intent parser for a spatial computer interface. "
    "Given a user utterance, respond ONLY with a JSON object: "
    '{"intent": "<INTENT_NAME>", "parameters": {<optional key-value pairs>}}. '
    "Allowed intent names: " + ", ".join(sorted(ALLOWED_INTENTS)) + ". "
    "Module names: home, music, camera, system, files, projects, ai assistant, 3d space, settings. "
    "For set_volume, include a 'value' parameter from 0.0 to 1.0. "
    "For open_module, include a 'target' parameter. "
    "NEVER output shell commands, code, or anything outside this JSON schema."
)


@dataclass
class OllamaConfig:
    url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:3b"
    timeout_seconds: float = 15.0


class OllamaAdapter:
    """Calls a local Ollama instance and parses the structured JSON response."""

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig(
            url=os.getenv("CYBERNETIC_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=os.getenv("CYBERNETIC_OLLAMA_MODEL", "llama3.2:3b"),
        )
        self.available = False
        self.error: str | None = None
        self._check_availability()

    def _check_availability(self) -> None:
        try:
            request = Request(f"{self.config.url}/api/tags", method="GET")
            with urlopen(request, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    if models:
                        self.available = True
                        if self.config.model not in models and not any(self.config.model in m for m in models):
                            self.config.model = models[0]
                    else:
                        self.available = True
                    return
        except Exception as exc:
            self.error = f"Ollama unavailable: {exc}"

    def parse_utterance(self, text: str) -> Intent | None:
        """Send a natural-language utterance to Ollama and parse the structured result."""
        if not self.available:
            return None
        try:
            payload = json.dumps({
                "model": self.config.model,
                "prompt": text,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 128},
            }).encode("utf-8")
            request = Request(
                f"{self.config.url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
            return self._extract_intent(result.get("response", ""))
        except Exception:
            return None

    def _extract_intent(self, raw: str) -> Intent | None:
        """Extract and validate the structured intent from the LLM response."""
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        json_str = raw[start : end + 1]
        try:
            parsed: dict[str, Any] = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback regex for simple single-level objects
            match = re.search(r"\{[^{}]+\}", raw)
            if not match:
                return None
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                return None

        intent_name = parsed.get("intent", "").lower().strip()
        if intent_name not in ALLOWED_INTENTS:
            return None

        parameters = parsed.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        # Sanitize parameters — only allow known safe types
        clean_params: dict[str, Any] = {}
        for key, value in parameters.items():
            if isinstance(value, (str, int, float, bool)):
                clean_params[str(key)] = value

        target = clean_params.pop("target", None)
        return Intent(
            name=intent_name,
            target=target,
            confidence=0.65,
            modalities=("voice", "llm"),
            parameters=clean_params,
        )

    @property
    def status(self) -> str:
        if self.available:
            return f"ONLINE ({self.config.model})"
        return f"OFFLINE ({self.error or 'not configured'})"
