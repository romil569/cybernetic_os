$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
& .\.venv\Scripts\python.exe main.py @args
