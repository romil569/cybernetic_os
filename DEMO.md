# Interactive Demonstration Script

**CYBERNETIC OS — Walkthrough & Demonstration Protocol**

---

## 1. System Launch & Diagnostic Telemetry

1. Open PowerShell and run:
   ```powershell
   .\scripts\run.ps1
   ```
2. Observe the startup console telemetry verifying:
   - Camera initialization
   - HandTracker (MediaPipe) readiness
   - SafeSystemController allowlist status
   - Local AI (Ollama) connectivity
   - Local 3D Spatial HTTP server startup (`http://127.0.0.1:8080`)

---

## 2. Spatial HUD & Navigation

- **Module Switching**: Perform a rapid **Swipe Left** or **Swipe Right** gesture to cycle across the 9 spatial desktop modules:
  `HOME` ➔ `MUSIC` ➔ `CAMERA` ➔ `SYSTEM` ➔ `FILES` ➔ `PROJECTS` ➔ `AI_ASSISTANT` ➔ `3D_SPACE` ➔ `SETTINGS`
- **Spatial Pointer**: Raise index finger in a **POINT** gesture to move the on-screen spatial target.
- **Pinch Action**: Bring index fingertip and thumb tip together (**PINCH**) to trigger an action on the active module.

---

## 3. Contextual Module Controls

### A. Music Module
- **Swipe Right**: Trigger Next Track (`MEDIA_NEXT`).
- **Swipe Left**: Trigger Previous Track (`MEDIA_PREV`).
- **Open Palm**: Toggle Play/Pause (`MEDIA_PLAY_PAUSE`).
- **Two-Finger Vertical Motion**: Continuous Windows master volume adjustment.

### B. Camera Module
- **Pinch**: Capture a high-resolution snapshot saved to `captures/capture_<timestamp>.jpg`.

### C. System Module
- **Pinch**: Query real-time OS metrics (CPU usage, RAM allocation, disk capacity) without executing shell scripts.

### D. 3D Spatial Space
- Press `3` or navigate to `3D_SPACE` to open `http://127.0.0.1:8080/`.
- **Swipe Left / Right**: Rotate 3D spatial artifact along the Y-axis.
- **Swipe Up / Down**: Rotate 3D spatial artifact along the X-axis.
- **Pinch**: Cycle between 3D geometries (Cube, Torus Knot, Icosahedron).

---

## 4. Calibration & Telemetry Review

1. Press **`C`** during runtime to trigger interactive spatial calibration, saving user thresholds to `config/user_profile.json`.
2. Press **`Q`** to exit cleanly.
3. Open `logs/performance.jsonl` to review true measured latency and framerate logs.
