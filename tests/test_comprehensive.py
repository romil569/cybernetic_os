"""Comprehensive test suite for CYBERNETIC OS.

Covers: event bus, gesture engine (all gestures + temporal states),
intent engine (voice map, context-aware gestures, multimodal fusion),
security, configuration, telemetry, and smoke tests.
"""
from pathlib import Path
from time import monotonic

from ai.intent_engine import IntentEngine, VoiceCommand
from ai.ollama_adapter import ALLOWED_INTENTS, OllamaAdapter
from core.config import ConfigStore, Settings
from core.events import EventBus
from core.models import GestureEvent, GestureName, GestureState, HandSnapshot, Landmark, Intent
from dashboard.hud import CyberneticDashboard
from gestures.engine import GestureEngine, GestureEngineConfig
from system_control.controller import SafeSystemController
from telemetry.metrics import Telemetry
from vision.hand_tracker import HandTracker


# ===========================================================================
# Helper to construct synthetic hand snapshots
# ===========================================================================

def hand_with(extended=(), pinch=False, velocity=(0.0, 0.0), thumb_up=False, thumb_down=False):
    """Build a synthetic HandSnapshot with controllable finger states."""
    landmarks = [Landmark(0.5, 0.7) for _ in range(21)]
    landmarks[0], landmarks[9] = Landmark(0.5, 0.7), Landmark(0.5, 0.5)
    for index, (tip, pip) in enumerate(((8, 6), (12, 10), (16, 14), (20, 18))):
        landmarks[pip] = Landmark(0.5 + index * .03, .55)
        landmarks[tip] = Landmark(0.5 + index * .03, .25 if index in extended else .7)
    # Thumb defaults
    landmarks[3], landmarks[4] = Landmark(.35, .55), Landmark(.25, .55)
    if pinch:
        landmarks[4], landmarks[8] = Landmark(.45, .40), Landmark(.46, .40)
    if thumb_up:
        # All fingers closed, thumb tip above thumb IP
        landmarks[3] = Landmark(.35, .55)
        landmarks[4] = Landmark(.35, .30)  # tip above IP
    if thumb_down:
        # All fingers closed, thumb tip below thumb IP
        landmarks[3] = Landmark(.35, .45)
        landmarks[4] = Landmark(.35, .70)  # tip below IP
    return HandSnapshot(landmarks, "Right", 1.0, (.5, .55), {}, velocity)


# ===========================================================================
# EVENT BUS
# ===========================================================================

def test_event_bus_publish_and_subscribe():
    bus = EventBus()
    received = []
    bus.subscribe("TestEvent", lambda event: received.append(event.payload))
    bus.publish("TestEvent", "hello")
    assert received == ["hello"]


def test_event_bus_unsubscribe():
    bus, received = EventBus(), []
    unsubscribe = bus.subscribe("GestureDetected", lambda event: received.append(event.payload))
    bus.publish("GestureDetected", "PINCH")
    unsubscribe()
    bus.publish("GestureDetected", "FIST")
    assert received == ["PINCH"]


def test_event_bus_payload():
    bus = EventBus()
    captured = []
    bus.subscribe("DataEvent", lambda e: captured.append(e))
    event = bus.publish("DataEvent", {"key": "value", "count": 42})
    assert event.name == "DataEvent"
    assert event.payload == {"key": "value", "count": 42}
    assert event.timestamp > 0
    assert captured[0].payload["count"] == 42


def test_event_bus_multiple_handlers():
    bus = EventBus()
    a, b = [], []
    bus.subscribe("X", lambda e: a.append(e.payload))
    bus.subscribe("X", lambda e: b.append(e.payload))
    bus.publish("X", 1)
    assert a == [1] and b == [1]


# ===========================================================================
# GESTURE ENGINE — Static Classification
# ===========================================================================

def test_classify_open_palm():
    engine = GestureEngine()
    assert engine.classify(hand_with(extended=(0, 1, 2, 3)))[0] == GestureName.OPEN_PALM


def test_classify_fist():
    engine = GestureEngine()
    assert engine.classify(hand_with())[0] == GestureName.FIST


def test_classify_point():
    engine = GestureEngine()
    assert engine.classify(hand_with(extended=(0,)))[0] == GestureName.POINT


def test_classify_pinch():
    engine = GestureEngine()
    assert engine.classify(hand_with(pinch=True))[0] == GestureName.PINCH


def test_classify_two_finger():
    engine = GestureEngine()
    assert engine.classify(hand_with(extended=(0, 1)))[0] == GestureName.TWO_FINGER


def test_classify_thumb_up():
    engine = GestureEngine()
    result = engine.classify(hand_with(thumb_up=True))
    assert result[0] == GestureName.THUMB_UP


def test_classify_thumb_down():
    engine = GestureEngine()
    result = engine.classify(hand_with(thumb_down=True))
    assert result[0] == GestureName.THUMB_DOWN


def test_classify_swipe_left():
    engine = GestureEngine(GestureEngineConfig(swipe_velocity=0.5))
    assert engine.classify(hand_with(extended=(0,), velocity=(-1.2, 0.0)))[0] == GestureName.SWIPE_LEFT


def test_classify_swipe_right():
    engine = GestureEngine(GestureEngineConfig(swipe_velocity=0.5))
    assert engine.classify(hand_with(extended=(0,), velocity=(1.2, 0.0)))[0] == GestureName.SWIPE_RIGHT


def test_classify_swipe_up():
    engine = GestureEngine(GestureEngineConfig(swipe_velocity=0.5))
    assert engine.classify(hand_with(extended=(0,), velocity=(0.0, -1.2)))[0] == GestureName.SWIPE_UP


def test_classify_swipe_down():
    engine = GestureEngine(GestureEngineConfig(swipe_velocity=0.5))
    assert engine.classify(hand_with(extended=(0,), velocity=(0.0, 1.2)))[0] == GestureName.SWIPE_DOWN


# ===========================================================================
# GESTURE ENGINE — Temporal Transitions
# ===========================================================================

def test_pinch_start_hold_release():
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=1, cooldown_seconds=0))
    started = engine.update(hand_with(pinch=True), now=1.0)
    held = engine.update(hand_with(pinch=True), now=1.1)
    released = engine.update(None, now=1.2)
    assert started and started.state == GestureState.START
    assert started.gesture == GestureName.PINCH
    assert held and held.state == GestureState.HOLD
    assert released and released.state == GestureState.RELEASE


def test_debounce_via_smoothing():
    """With smoothing=3, a single-frame gesture should not produce START."""
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=3, cooldown_seconds=0))
    # One frame of pinch surrounded by no-hand
    engine.update(None, now=1.0)
    engine.update(None, now=1.1)
    result = engine.update(hand_with(pinch=True), now=1.2)
    # The single pinch frame is outvoted by NONE in the buffer
    assert result is None


def test_cooldown_suppresses_repeated_gestures():
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=1, cooldown_seconds=1.0, swipe_velocity=.5))
    first = engine.update(hand_with(extended=(0,), velocity=(1.0, 0.0)), now=10.0)
    engine.update(None, now=10.1)  # release
    suppressed = engine.update(hand_with(extended=(0,), velocity=(1.0, 0.0)), now=10.4)
    assert first and first.gesture == GestureName.SWIPE_RIGHT
    assert suppressed is None  # within cooldown


def test_cooldown_allows_after_period():
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=1, cooldown_seconds=0.5, swipe_velocity=.5))
    engine.update(hand_with(extended=(0,), velocity=(1.0, 0.0)), now=10.0)
    engine.update(None, now=10.1)
    # After cooldown period passes
    allowed = engine.update(hand_with(extended=(0,), velocity=(1.0, 0.0)), now=10.6)
    assert allowed and allowed.gesture == GestureName.SWIPE_RIGHT


def test_hysteresis_stable_gesture():
    """Smoothing creates hysteresis — gesture must be stable across multiple frames."""
    engine = GestureEngine(GestureEngineConfig(smoothing_frames=3, cooldown_seconds=0))
    # Feed 3 frames of pinch to fill buffer
    engine.update(hand_with(pinch=True), now=1.0)
    engine.update(hand_with(pinch=True), now=1.1)
    result = engine.update(hand_with(pinch=True), now=1.2)
    assert result and result.gesture == GestureName.PINCH


# ===========================================================================
# INTENT ENGINE — Voice Commands
# ===========================================================================

def test_voice_play_music():
    intent = IntentEngine().resolve(VoiceCommand("play music"), None, "home")
    assert intent and intent.name == "media_play_pause"


def test_voice_pause_music():
    intent = IntentEngine().resolve(VoiceCommand("pause music"), None, "home")
    assert intent and intent.name == "media_play_pause"


def test_voice_next_song():
    intent = IntentEngine().resolve(VoiceCommand("next song"), None, "home")
    assert intent and intent.name == "media_next"


def test_voice_volume_up():
    intent = IntentEngine().resolve(VoiceCommand("turn volume up"), None, "home")
    assert intent and intent.name == "adjust_volume"
    assert intent.parameters.get("direction") == "up"


def test_voice_take_photo():
    intent = IntentEngine().resolve(VoiceCommand("take a photo"), None, "home")
    assert intent and intent.name == "capture_photo"


def test_voice_open_projects():
    intent = IntentEngine().resolve(VoiceCommand("open projects"), None, "home")
    assert intent and intent.name == "open_module" and intent.target == "projects"


def test_voice_open_system():
    intent = IntentEngine().resolve(VoiceCommand("open system"), None, "home")
    assert intent and intent.name == "open_module" and intent.target == "system"


def test_voice_go_home():
    intent = IntentEngine().resolve(VoiceCommand("go home"), None, "music")
    assert intent and intent.name == "open_module" and intent.target == "home"


def test_voice_set_volume_numeric():
    intent = IntentEngine().resolve(VoiceCommand("set volume to 50 percent"), None, "home")
    assert intent and intent.name == "set_volume"
    assert abs(intent.parameters["value"] - 0.5) < 0.01


# ===========================================================================
# INTENT ENGINE — Multimodal Fusion
# ===========================================================================

def test_multimodal_voice_plus_gesture_target():
    """Voice says 'open music' but finger points at 'projects' → projects wins."""
    intent = IntentEngine().resolve(VoiceCommand("open music"), None, "home", "projects")
    assert intent and intent.name == "open_module" and intent.target == "projects"
    assert "voice" in intent.modalities and "gesture" in intent.modalities


def test_multimodal_gesture_only():
    pinch = GestureEvent(GestureName.PINCH, GestureState.START, .9, 1.0)
    intent = IntentEngine().resolve(None, pinch, "home", "music")
    assert intent and intent.name == "activate"


# ===========================================================================
# INTENT ENGINE — Context-Aware Gestures
# ===========================================================================

def test_context_music_swipe_right_is_media_next():
    gesture = GestureEvent(GestureName.SWIPE_RIGHT, GestureState.START, .85, 1.0)
    intent = IntentEngine().resolve(None, gesture, "music")
    assert intent and intent.name == "media_next"


def test_context_3d_swipe_right_is_rotate():
    gesture = GestureEvent(GestureName.SWIPE_RIGHT, GestureState.START, .85, 1.0)
    intent = IntentEngine().resolve(None, gesture, "3d space")
    assert intent and intent.name == "rotate_right"


def test_context_home_swipe_right_is_next_module():
    gesture = GestureEvent(GestureName.SWIPE_RIGHT, GestureState.START, .85, 1.0)
    intent = IntentEngine().resolve(None, gesture, "home")
    assert intent and intent.name == "next_module"


def test_context_camera_pinch_is_capture():
    gesture = GestureEvent(GestureName.PINCH, GestureState.START, .9, 1.0)
    intent = IntentEngine().resolve(None, gesture, "camera")
    assert intent and intent.name == "capture_photo"


# ===========================================================================
# SECURITY
# ===========================================================================

def test_system_control_rejects_unlisted_action(tmp_path: Path):
    controller = SafeSystemController([tmp_path])
    assert controller.validate("set_volume")
    assert controller.validate("media_play_pause")
    assert not controller.validate("run_powershell")
    assert not controller.validate("exec_cmd")
    assert not controller.validate("rm_rf")
    assert not controller.validate("os.system")
    assert not controller.execute("run_powershell").ok


def test_system_control_blocks_arbitrary_shell():
    controller = SafeSystemController([])
    for dangerous in ["eval", "exec", "subprocess", "os.system", "powershell",
                      "cmd /c", "rm -rf", "del /f", "format c:"]:
        assert not controller.validate(dangerous)
        result = controller.execute(dangerous)
        assert not result.ok
        assert "Blocked" in result.message


def test_system_control_folder_allowlist(tmp_path: Path):
    allowed = tmp_path / "safe"
    allowed.mkdir()
    controller = SafeSystemController([allowed])
    # Should block a path outside the allowlist
    result = controller.open_folder(Path("C:/Windows/System32"))
    assert not result.ok
    assert "Blocked" in result.message


def test_system_control_app_allowlist():
    controller = SafeSystemController([])
    # Should block arbitrary executables
    result = controller.launch_app("malware.exe")
    assert not result.ok
    assert "not in the launch allowlist" in result.message


def test_ollama_intent_vocabulary():
    """Verify the LLM adapter only allows the curated intent set."""
    dangerous = {"run_shell", "execute_command", "delete_file", "format_disk"}
    assert not dangerous & ALLOWED_INTENTS


def test_ollama_extract_rejects_bad_intent():
    adapter = OllamaAdapter.__new__(OllamaAdapter)
    adapter.available = False
    adapter.config = None
    adapter.error = "test"
    # Even if we call _extract_intent directly with dangerous JSON:
    result = adapter._extract_intent('{"intent": "run_shell", "parameters": {"cmd": "rm -rf /"}}')
    assert result is None  # run_shell is not in ALLOWED_INTENTS


# ===========================================================================
# CONFIGURATION
# ===========================================================================

def test_config_round_trip(tmp_path: Path):
    store = ConfigStore(tmp_path)
    settings = Settings(camera_index=2, cursor_sensitivity=1.4,
                        pinch_threshold=0.45, swipe_sensitivity=0.8)
    store.save(settings)
    loaded = store.load()
    assert loaded.camera_index == 2
    assert loaded.cursor_sensitivity == 1.4
    assert abs(loaded.pinch_threshold - 0.45) < 0.01
    assert abs(loaded.swipe_sensitivity - 0.8) < 0.01


def test_config_profile_round_trip(tmp_path: Path):
    store = ConfigStore(tmp_path)
    store.save_profile({"calibrated": True, "samples": {"PINCH": [.8, .9]}})
    profile = store.load_profile()
    assert profile["calibrated"] is True
    assert len(profile["samples"]["PINCH"]) == 2


def test_config_handles_missing_file(tmp_path: Path):
    store = ConfigStore(tmp_path)
    settings = store.load()
    assert settings.camera_index == 0  # default


def test_config_forward_compatible(tmp_path: Path):
    """Unknown keys in JSON should not crash loading."""
    import json
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(
        json.dumps({"camera_index": 3, "unknown_future_key": True}),
        encoding="utf-8",
    )
    store = ConfigStore(tmp_path)
    settings = store.load()
    assert settings.camera_index == 3


# ===========================================================================
# TELEMETRY
# ===========================================================================

def test_telemetry_records_without_crashing(tmp_path: Path):
    telemetry = Telemetry(tmp_path / "perf.jsonl")
    telemetry.record(30.0, 3.5, 35.0, 0, "PINCH:START", 0.9)
    telemetry.record(25.0, 4.0, 40.0, 1, "NONE", 0.0)
    assert (tmp_path / "perf.jsonl").exists()
    lines = (tmp_path / "perf.jsonl").read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_telemetry_summary(tmp_path: Path):
    telemetry = Telemetry(tmp_path / "perf.jsonl")
    for fps in [20.0, 30.0, 40.0]:
        telemetry.record(fps, 3.0, 35.0, 0)
    summary = telemetry.summary()
    assert abs(summary["avg_fps"] - 30.0) < 0.01
    assert summary["min_fps"] == 20.0
    assert summary["samples"] == 3.0


# ===========================================================================
# SMOKE TESTS
# ===========================================================================

def test_dashboard_has_all_modules():
    dashboard = CyberneticDashboard()
    assert len(dashboard.MODULES) == 9
    expected = {"home", "music", "camera", "system", "files", "projects",
                "ai assistant", "3d space", "settings"}
    assert set(dashboard.MODULES) == expected


def test_dashboard_module_navigation():
    dashboard = CyberneticDashboard()
    assert dashboard.next_module() == "music"
    assert dashboard.next_module() == "camera"
    assert dashboard.next_module(-1) == "music"


def test_hand_tracker_initializes_or_explains_unavailability():
    tracker = HandTracker()
    assert tracker.available or tracker.error
    tracker.close()


def test_3d_page_is_present():
    page = Path(__file__).parents[1] / "spatial_ui" / "three_d.html"
    content = page.read_text(encoding="utf-8")
    assert "THREE.WebGLRenderer" in content
    assert "three.module.js" in content


def test_three_js_vendor_exists():
    vendor = Path(__file__).parents[1] / "spatial_ui" / "vendor" / "three.module.js"
    assert vendor.exists()
    assert vendor.stat().st_size > 100_000  # Three.js is a large file


def test_all_modules_import():
    """Verify all major modules can be imported without errors."""
    from core.events import EventBus
    from core.models import GestureName
    from core.config import ConfigStore
    from vision.camera import Camera
    from vision.hand_tracker import HandTracker
    from gestures.engine import GestureEngine
    from ai.intent_engine import IntentEngine
    from ai.ollama_adapter import OllamaAdapter
    from dashboard.hud import CyberneticDashboard
    from system_control.controller import SafeSystemController
    from system_control.cursor import SpatialCursor
    from telemetry.metrics import Telemetry
    from spatial_ui.web_server import SpatialWebServer
    from voice.recognizer import VoiceRecognizer
    assert True  # If we get here, all imports succeeded
