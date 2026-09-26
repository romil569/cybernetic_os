from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import sleep

from ai.intent_engine import IntentEngine, VoiceCommand
from ai.ollama_adapter import OllamaAdapter
from core.config import ConfigStore
from core.events import EventBus
from core.models import GestureEvent, GestureName, GestureState, Intent
from dashboard.hud import CyberneticDashboard
from gestures.engine import GestureEngine, GestureEngineConfig
from spatial_ui.web_server import SpatialWebServer
from system_control.controller import SafeSystemController
from system_control.cursor import SpatialCursor
from telemetry.metrics import Telemetry
from vision.camera import Camera
from vision.hand_tracker import HandTracker
from voice.recognizer import VoiceRecognizer


ROOT = Path(__file__).resolve().parent


class CyberneticOS:
    def __init__(self, headless: bool = False, cursor_control: bool = False) -> None:
        self.headless = headless
        self.config_store = ConfigStore(ROOT)
        self.settings = self.config_store.load()
        self.events = EventBus()
        self.camera = Camera(self.settings.camera_index, self.settings.width, self.settings.height)
        self.tracker = HandTracker(
            max_hands=2,
            min_detection=self.settings.confidence_threshold,
            min_tracking=self.settings.confidence_threshold,
        )
        self.gestures = GestureEngine(GestureEngineConfig(
            cooldown_seconds=self.settings.gesture_cooldown_seconds,
            pinch_ratio=self.settings.pinch_threshold,
            swipe_velocity=self.settings.swipe_sensitivity,
            smoothing_frames=self.settings.smoothing_frames,
        ))
        self.intent_engine = IntentEngine()
        self.ollama = OllamaAdapter()
        self.dashboard = CyberneticDashboard()
        self.voice = VoiceRecognizer()
        self.system = SafeSystemController([ROOT, Path.home() / "Desktop", Path.home() / "Documents"])
        self.cursor = SpatialCursor(self.settings.cursor_sensitivity, cursor_control)
        self.telemetry = Telemetry(ROOT / "logs" / "performance.jsonl")
        self.spatial = SpatialWebServer(ROOT / "spatial_ui")
        self.running = True
        self.last_frame = None
        self.calibration_steps = ["OPEN_PALM", "FIST", "PINCH", "POINT", "SWIPE_LEFT", "SWIPE_RIGHT"]
        self.calibration_index: int | None = None
        self.calibration_samples: dict[str, list[float]] = {}
        self.events.subscribe("IntentRecognized", self._handle_intent)

    def startup(self) -> None:
        print("CYBERNETIC OS")
        print("Initializing Camera...")
        print("Initializing Vision...", "ONLINE" if self.tracker.available else self.tracker.error)
        print("Initializing Gesture Engine... ONLINE")
        print("Initializing Spatial UI... ONLINE")
        print("Initializing Voice...", self.voice.status)
        print("Initializing AI...", self.ollama.status)
        print("SYSTEM ONLINE")
        self.dashboard.state.voice_status = self.voice.status
        self.dashboard.state.ai_status = self.ollama.status

    def run(self, max_frames: int | None = None) -> int:
        self.startup()
        if not self.camera.start():
            self.dashboard.state.camera_status = "OFFLINE"
            print(f"CAMERA: OFFLINE - {self.camera.error}")
            return 0 if self.headless else 2
        import cv2
        frame_count = 0
        try:
            while self.running:
                packet = self.camera.read()
                if packet is None:
                    print(f"CAMERA ERROR: {self.camera.error}")
                    break
                frame = cv2.flip(packet.image, 1)
                self.last_frame = frame.copy()
                hands, inference_ms = self.tracker.process(frame, draw=True)
                self.dashboard.state.hand_mode = "TWO_HAND_MODE" if len(hands) >= 2 else "ONE_HAND_MODE"
                hand = hands[0] if hands else None
                if hand and self.cursor.enabled:
                    self.cursor.update((hand.index_tip.x, hand.index_tip.y))
                    self.dashboard.select_from_point(hand.fingertip_pixels["index"], frame.shape)
                event = self.gestures.update(hand)
                if event:
                    self._on_gesture(event, hands)
                self.dashboard.state.fps = packet.fps
                self.dashboard.state.latency_ms = packet.frame_latency_ms + inference_ms
                self.telemetry.record(packet.fps, packet.frame_latency_ms, inference_ms, packet.dropped_frames, self.dashboard.state.gesture, self.dashboard.state.confidence)
                if not self.headless:
                    cv2.imshow("Cybernetic OS - press Q to quit, C to calibrate, 3 for 3D", self.dashboard.render(frame))
                    self._handle_key(cv2.waitKey(1) & 0xFF)
                frame_count += 1
                if max_frames and frame_count >= max_frames:
                    break
        finally:
            self.camera.release()
            self.tracker.close()
            self.spatial.stop()
            if not self.headless:
                cv2.destroyAllWindows()
        print("SYSTEM OFFLINE")
        return 0

    def _on_gesture(self, event: GestureEvent, hands) -> None:
        self.dashboard.state.gesture = f"{event.gesture.value}:{event.state.value}"
        self.dashboard.state.confidence = event.confidence
        self.events.publish("GestureDetected", event)
        if self.calibration_index is not None and event.state == GestureState.START:
            expected = self.calibration_steps[self.calibration_index]
            if event.gesture.value == expected:
                self.calibration_samples.setdefault(expected, []).append(event.confidence)
                self.calibration_index += 1
                if self.calibration_index == len(self.calibration_steps):
                    self.config_store.save_profile({"calibrated": True, "samples": self.calibration_samples})
                    self.calibration_index = None
                    self.dashboard.state.message = "CALIBRATION SAVED LOCALLY"
                else:
                    self.dashboard.state.message = f"CALIBRATION: show {self.calibration_steps[self.calibration_index]}"
        target = self.dashboard.state.selected_module
        intent = self.intent_engine.resolve(None, event, self.dashboard.state.module, target)
        if intent:
            self.events.publish("IntentRecognized", intent)
        if len(hands) >= 2 and event.gesture == GestureName.PINCH:
            self.spatial.command("scale")

    def _handle_intent(self, event) -> None:
        intent: Intent = event.payload
        self.events.publish("ActionRequested", intent)

        # Navigation intents
        if intent.name == "open_module" and intent.target in self.dashboard.MODULES:
            self.dashboard.state.module = intent.target
            self.dashboard.state.selected_module = intent.target
            self.dashboard.state.message = f"OPENED {intent.target.upper()}"
            self.events.publish("ModuleSelected", intent.target)
        elif intent.name == "next_module":
            self.dashboard.state.message = f"OPENED {self.dashboard.next_module(1).upper()}"
        elif intent.name == "previous_module":
            self.dashboard.state.message = f"OPENED {self.dashboard.next_module(-1).upper()}"

        # Activation intents
        elif intent.name == "activate":
            self._activate(intent.target)

        # Media transport
        elif intent.name == "media_play_pause":
            result = self.system.execute("media_play_pause")
            self.dashboard.state.message = result.message
        elif intent.name == "media_next":
            result = self.system.execute("media_next")
            self.dashboard.state.message = result.message
        elif intent.name == "media_previous":
            result = self.system.execute("media_previous")
            self.dashboard.state.message = result.message

        # Volume
        elif intent.name == "set_volume":
            value = intent.parameters.get("value", 0.5)
            result = self.system.execute("set_volume", value=value)
            self.dashboard.state.message = result.message
            self.dashboard.state.volume = value if result.ok else None
        elif intent.name == "adjust_volume":
            direction = intent.parameters.get("direction", "up")
            current = self.system._volume or 0.5
            new_value = min(1.0, current + 0.1) if direction == "up" else max(0.0, current - 0.1)
            result = self.system.execute("set_volume", value=new_value)
            self.dashboard.state.message = result.message
            self.dashboard.state.volume = new_value if result.ok else None

        # Mute
        elif intent.name == "mute":
            result = self.system.execute("mute")
            self.dashboard.state.message = result.message

        # Camera capture
        elif intent.name == "capture_photo":
            self._capture_photo()

        # System info
        elif intent.name == "system_info":
            result = self.system.execute("system_info")
            self.dashboard.state.message = result.message

        # Screenshot
        elif intent.name == "screenshot":
            result = self.system.execute("screenshot")
            self.dashboard.state.message = result.message

        # 3D space commands
        elif intent.name in ("rotate_left", "rotate_right", "rotate_up", "rotate_down", "select_3d", "reset_view"):
            self.spatial.command(intent.name)
            self.dashboard.state.message = f"3D: {intent.name.replace('_', ' ').upper()}"

        # Confirmation/cancellation
        elif intent.name == "confirm":
            self.dashboard.state.message = "CONFIRMED"
        elif intent.name == "cancel":
            self.dashboard.state.message = "CANCELLED"

    def _activate(self, target: str | None) -> None:
        module = target or self.dashboard.state.module
        if module == "camera":
            self._capture_photo()
        elif module == "3d space":
            url = self.spatial.open()
            self.dashboard.state.message = "3D SPACE OPENED" if url else "3D SERVER PORT UNAVAILABLE"
        elif module == "system":
            result = self.system.execute("system_info")
            self.dashboard.state.message = result.message
        elif module == "files":
            result = self.system.execute("open_folder", folder=ROOT)
            self.dashboard.state.message = result.message
        else:
            self.dashboard.state.message = f"{module.upper()} ACTIVE"

    def _capture_photo(self) -> None:
        if self.last_frame is None:
            self.dashboard.state.message = "PHOTO FAILED: NO FRAME"
            return
        import cv2
        from datetime import datetime
        destination = ROOT / "captures" / f"capture-{datetime.now():%Y%m%d-%H%M%S}.jpg"
        cv2.imwrite(str(destination), self.last_frame)
        self.dashboard.state.message = f"PHOTO CAPTURED: {destination.name}"
        self.events.publish("CameraCaptured", str(destination))

    def _handle_key(self, key: int) -> None:
        if key in (ord("q"), 27): self.running = False
        elif key == ord("c"):
            self.calibration_index, self.calibration_samples = 0, {}
            self.dashboard.state.message = f"CALIBRATION: show {self.calibration_steps[0]}"
        elif key == ord("3"):
            self.dashboard.state.module = "3d space"; self._activate("3d space")
        elif key == ord("["):
            self.dashboard.next_module(-1)
        elif key == ord("]"):
            self.dashboard.next_module(1)
        elif key == ord("m"):
            value = self.system._volume if self.system._volume is not None else 0.5
            result = self.system.execute("set_volume", value=value)
            self.dashboard.state.message = result.message
            self.dashboard.state.volume = value if result.ok else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CYBERNETIC OS multimodal spatial interface")
    parser.add_argument("--headless", action="store_true", help="Run startup and camera checks without creating a window.")
    parser.add_argument("--frames", type=int, default=None, help="Stop after N acquired frames; useful for integration checks.")
    parser.add_argument("--cursor-control", action="store_true", help="Allow hand tracking to move the Windows cursor.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(CyberneticOS(args.headless, args.cursor_control).run(args.frames))
