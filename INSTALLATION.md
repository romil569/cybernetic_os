# Installation Guide

**CYBERNETIC OS — Environment Setup & Dependencies**

---

## 1. Prerequisites

- **Operating System**: Windows 10/11 (x64)
- **Python**: Python 3.10 – 3.12 (Python 3.12 recommended)
- **Webcam**: Standard USB or Integrated 720p/1080p webcam
- **Audio Output**: Windows Default Audio Device (for volume controls)
- **Optional Local LLM**: [Ollama](https://ollama.com/) running locally on `http://localhost:11434`

---

## 2. Automated One-Step Setup (Recommended)

From PowerShell in the project directory (`C:\Users\HP\Desktop\cybernetic_os`):

```powershell
.\scripts\setup.ps1
```

Or explicitly skip physical camera initialization if running in a headless or CI environment:

```powershell
.\scripts\setup.ps1 -SkipCameraCheck
```

### What Setup Does:
1. Verifies Python 3.12 availability.
2. Creates the local virtual environment `.venv`.
3. Installs pinned dependencies (`requirements.txt`).
4. Verifies binary compatibility between OpenCV, MediaPipe, and NumPy.
5. Generates runtime storage directories (`captures/`, `logs/`, `config/`).
6. Executes the automated test suite (`pytest`).
7. Runs a single-frame headless smoke test.

---

## 3. Manual Installation

If you prefer manual setup:

```powershell
# 1. Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install pinned requirements
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 3. Create required runtime directories
mkdir -Force captures, logs, config

# 4. Run tests
python -m pytest tests/ -v
```

---

## 4. Running the Application

### Real-Time Spatial Interface (with Webcam):
```powershell
.\scripts\run.ps1
# Or directly:
.\.venv\Scripts\python.exe main.py
```

### Headless Mode (Development / CI / No Camera):
```powershell
.\.venv\Scripts\python.exe main.py --headless --frames 60
```

### Running Test Suite:
```powershell
.\scripts\test.ps1
```
