# Architecture Specification

**CYBERNETIC OS — AI-Powered Multimodal Spatial Computer Interface**

---

## 1. System Pipeline Overview

```
WEBCAM FRAME
     │
     ▼
┌─────────────────────────┐
│     vision/camera       │  Acquires raw frames, measures camera latency, handles offline status
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   vision/hand_tracker   │  MediaPipe Hand Landmarker (up to 2 hands, 21 3D landmarks/hand)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     gestures/engine     │  Deterministic geometric classification + Temporal state machines
└────────────┬────────────┘  (FSM: IDLE -> START -> HOLD -> RELEASE with debounce & cooldown)
             │
             ▼
┌─────────────────────────┐
│    ai/intent_engine     │  Fuses GESTURE + VOICE + CONTEXT + OPTIONAL LOCAL LLM (Ollama)
└────────────┬────────────┘  (Produces safe typed Intent instances — NO arbitrary shell execution)
             │
     ┌───────┴──────────────────────────────┐
     │                                      │
     ▼                                      ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│ system_control/         │    │ spatial_ui/             │
│ controller.py           │    │ - OpenCV HUD (dashboard)│
│ (Allowlisted OS actions)│    │ - Local 3D WebGL Scene  │
└─────────────────────────┘    └─────────────────────────┘
     │                                      │
     └───────────────────┬──────────────────┘
                         │
                         ▼
               ┌───────────────────┐
               │ telemetry/logger  │  Local performance logging (JSONL)
               └───────────────────┘
```

---

## 2. Core Subsystems

### `core/`
- **`events.py`**: Synchronous, strongly-typed `EventBus` managing lifecycle signals (`GestureDetected`, `IntentRecognized`, `ModuleSelected`, `ActionRequested`, `CameraCaptured`). Ensures predictable, thread-safe message dispatch.
- **`models.py`**: Immutable dataclasses and Enums (`HandLandmarks`, `GestureEvent`, `GestureName`, `GestureState`, `Intent`, `SystemMetric`).
- **`config.py`**: `ConfigStore` and `Settings` supporting dynamic runtime calibration (pinch threshold, swipe sensitivity, cursor smoothing, confidence thresholds).

### `vision/`
- **`camera.py`**: Safe camera capture abstraction supporting index switching, frame latency measurement, and graceful offline fallback.
- **`hand_tracker.py`**: MediaPipe Hands wrapper providing landmark smoothing, multi-hand tracking, and confidence thresholding.

### `gestures/`
- **`engine.py`**: Two-stage gesture pipeline:
  1. **Spatial Classifier**: Evaluates Euclidean geometric distances and finger extension states for 11 distinct gestures: `OPEN_PALM`, `FIST`, `POINT`, `PINCH`, `TWO_FINGER`, `THUMB_UP`, `THUMB_DOWN`, `SWIPE_LEFT`, `SWIPE_RIGHT`, `SWIPE_UP`, `SWIPE_DOWN`.
  2. **Temporal Engine**: Per-hand finite-state tracking managing `PINCH_START`, `PINCH_HOLD`, `PINCH_RELEASE` transitions with configurable debounce (frames) and cooldown hysteresis (seconds).

### `ai/`
- **`intent_engine.py`**: Context-aware intent resolution mapping gestures and voice triggers to discrete actions depending on the active module (e.g. `MUSIC` vs `3D_SPACE` vs `HOME`).
- **`ollama_adapter.py`**: Optional local LLM interface connecting to Ollama (`localhost:11434`) for structured JSON intent extraction. Fails gracefully if Ollama is offline.

### `system_control/`
- **`controller.py`**: Security-hardened system interface executing only allowlisted system operations (Windows CoreAudio volume via `pycaw`, standard media virtual keys via `win32api`, screenshot capture, allowlisted app launch, system status queries).

### `spatial_ui/` & `dashboard/`
- **`hud.py`**: OpenCV real-time visual overlay rendering module selector, active gestures, confidence indicators, and live telemetry.
- **`three_d.html` & `server.py`**: Self-hosted local Three.js spatial viewport featuring interactive geometry, gesture state telemetry HUD, rotation/scale manipulation, and loopback-only HTTP server.

### `telemetry/`
- **`logger.py`**: `TelemetryCollector` recording true measured metrics (FPS, camera acquisition latency, inference duration, action latency, dropped frames) to `logs/performance.jsonl`.
