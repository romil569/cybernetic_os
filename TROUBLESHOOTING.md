# Troubleshooting & Diagnostics

**CYBERNETIC OS — Operational Diagnostics & Resolution**

---

## 1. Camera & Video Issues

### Issue: "Camera offline" or "Failed to open camera index 0"
- **Cause**: Another desktop application (e.g. Teams, Zoom, Discord, Windows Camera) is holding an exclusive handle to the webcam, or camera permissions are disabled in Windows Settings.
- **Resolution**:
  1. Close any conflicting camera software.
  2. Open Windows Settings → Privacy & Security → Camera → Enable "Let desktop apps access your camera".
  3. If you have multiple webcams, change `"camera_index": 1` in `config/settings.json` or pass `--camera-index 1`.
  4. Cybernetic OS degrades safely to offline mode without crashing.

---

## 2. MediaPipe & Python Runtime Issues

### Issue: Import errors or binary conflicts between OpenCV and MediaPipe
- **Cause**: Incompatible Python version or NumPy 2.x ABI incompatibility.
- **Resolution**:
  1. Ensure you are running Python 3.12 (Python 3.13+ is not yet fully supported by MediaPipe C++ wheels).
  2. Use pinned versions: `numpy==1.26.4`, `opencv-contrib-python==4.11.0.86`, `mediapipe==0.10.21`.
  3. Re-run `.\scripts\setup.ps1` to rebuild `.venv`.

---

## 3. Audio & System Control Issues

### Issue: Master volume changes do not affect system sound
- **Cause**: Windows CoreAudio endpoint (`pycaw`) unavailable or running in a headless / non-audio session.
- **Resolution**:
  - The application automatically catches `pycaw` initialization errors and flags `SafeSystemController.available = False`.
  - Vision and gesture modules continue operating unaffected.

---

## 4. Local AI (Ollama) Integration

### Issue: "Ollama offline — using local intent engine"
- **Cause**: Ollama service is not running on `http://localhost:11434`.
- **Resolution**:
  - Start Ollama service (`ollama serve`) and pull a model (e.g. `ollama pull llama3.2` or `mistral`).
  - Cybernetic OS operates seamlessly in offline rule-based intent mode when Ollama is unavailable.

---

## 5. Local 3D Spatial Viewport Issues

### Issue: 3D scene shows a blank canvas or WebGL error
- **Cause**: WebGL disabled or port 8080 collision.
- **Resolution**:
  - Ensure your browser has Hardware Acceleration and WebGL enabled.
  - The 3D viewport uses vendored Three.js at `spatial_ui/vendor/three.min.js` and requires no internet connection.
  - If port 8080 is occupied, adjust port in `spatial_ui/server.py`.
