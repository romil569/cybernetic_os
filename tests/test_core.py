"""Core module integration tests — preserved from the original test suite."""
from pathlib import Path

from ai.intent_engine import IntentEngine, VoiceCommand
from core.config import ConfigStore, Settings
from core.events import EventBus
from core.models import GestureEvent, GestureName, GestureState
from system_control.controller import SafeSystemController


def test_event_bus_delivers_and_unsubscribes():
    bus, received = EventBus(), []
    unsubscribe = bus.subscribe("GestureDetected", lambda event: received.append(event.payload))
    bus.publish("GestureDetected", "PINCH")
    unsubscribe()
    bus.publish("GestureDetected", "FIST")
    assert received == ["PINCH"]


def test_config_round_trip(tmp_path: Path):
    store = ConfigStore(tmp_path)
    settings = Settings(camera_index=2, cursor_sensitivity=1.4)
    store.save(settings)
    assert store.load().camera_index == 2
    store.save_profile({"calibrated": True, "samples": {"PINCH": [.8]}})
    assert store.load_profile()["calibrated"] is True


def test_multimodal_intent_prefers_pointed_target():
    intent = IntentEngine().resolve(VoiceCommand("open music"), None, "home", "projects")
    assert intent and intent.name == "open_module" and intent.target == "projects"
    pinch = GestureEvent(GestureName.PINCH, GestureState.START, .9, 1.0)
    gesture_intent = IntentEngine().resolve(None, pinch, "home", "music")
    assert gesture_intent and gesture_intent.name == "activate"


def test_system_control_rejects_unlisted_action(tmp_path: Path):
    controller = SafeSystemController([tmp_path])
    assert controller.validate("set_volume")
    assert not controller.validate("run_powershell")
    assert not controller.execute("run_powershell").ok
