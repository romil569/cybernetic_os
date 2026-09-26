param([switch]$SkipCameraCheck)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python launcher (py) was not found. Install Python 3.10-3.12 first." }
$pythonVersion = & py -3.12 --version
Write-Host "Using $pythonVersion"

if (-not (Test-Path .venv)) { & py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install --use-deprecated=legacy-resolver -r requirements.txt
& .\.venv\Scripts\python.exe -c "import cv2, mediapipe, numpy; print('Imports OK:', cv2.__version__, mediapipe.__version__, numpy.__version__)"
New-Item -ItemType Directory -Force captures, logs, config | Out-Null
& .\.venv\Scripts\python.exe -m pytest
if (-not $SkipCameraCheck) { & .\.venv\Scripts\python.exe main.py --headless --frames 1 }
Write-Host "Setup complete. Start with: .\.venv\Scripts\python.exe main.py"
