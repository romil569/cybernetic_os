param([switch]$SkipCameraCheck)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

& "$PSScriptRoot\setup_windows.ps1" -SkipCameraCheck:$SkipCameraCheck
