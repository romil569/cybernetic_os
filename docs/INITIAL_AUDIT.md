# Initial source audit

| Source | Purpose and entry point | Useful material | Weaknesses and disposition |
|---|---|---|---|
| Hand-Tracking-AR-UI | `main.py`: single-camera AR overlay with MediaPipe Hands | OpenCV overlay ideas, radial HUD vocabulary | One global loop, one hand only, no lifecycle/error handling, threshold-only gesture states. Refactor conceptually; do not copy source. |
| Cybernetic-AR-HUD | `main.py`: face, hands and pose HUD; `hud.py`, `gestures.py`, `utils.py` | Status-oriented HUD concept and face/hand integration direction | MediaPipe Solutions API, coupled renderer/state, decorative evolution values, no measured latency. HUD is replaced with measured system status. |
| AirSwipe-Music-Controller | `gesture_spotify_player.py` | Swipe/media semantics, Spotify/local playback fallback concept | Long single script, optional Spotify credentials, gesture/UI logic coupled, experimental notebook. Media actions are an explicit optional integration boundary. |
| Hand-Based-Sound-Controller | `main.py`, `hand_tracker.py`, `audio_controller.py` | Windows `pycaw` endpoint approach and smoothed finger-distance volume | One-hand-only tracking, deprecated simple y thresholds, no action validation. Volume adapter is retained behind allowlist checks. |
| AirClick-Camera | Supplied URL | None available | `https://github.com/tubakhxn/AirClick-Camera` returned GitHub `Repository not found` on 2026-09-26. It cannot be audited or cloned. Camera capture is independently implemented and this missing source is not represented as integrated. |

## Dependencies and versions found

The source repositories do not pin a Python version. Their requirements use unpinned `opencv-python`, `mediapipe`, and `numpy<2`; HUD additionally lists `pygame`. Their code uses the legacy `mp.solutions` APIs. CYBERNETIC OS selects Python 3.12, OpenCV Contrib 4.11, MediaPipe 0.10.21 and NumPy 1.26.4, all explicitly pinned in `requirements.txt`.

## Keep, refactor, replace, merge, remove

- Keep: local-first OpenCV frame processing, MediaPipe landmarks, HUD information hierarchy, swipe navigation semantics, and the pycaw master-volume mechanism.
- Refactor: tracking into `vision/hand_tracker.py`, gestures into `gestures/engine.py`, UI into `dashboard/hud.py`, and configuration into `core/config.py`.
- Replace: global loops, hard-coded unmeasured status numbers, gesture side effects, and direct controller calls with the event bus, temporal engine and allowlisted action boundary.
- Merge: camera, gesture, music/volume semantics, capture, and HUD concepts through `main.py` rather than copying folders or code.
- Remove from the new application: Spotify credentials and arbitrary external playback assumptions; source repositories remain untouched in `original_projects/`.
