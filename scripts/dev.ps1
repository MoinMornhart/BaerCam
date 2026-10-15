# Startet BärCam im Entwicklungsmodus (Oberfläche + Backend aus dem Dev-venv).
# Rust-Build-Dateien landen außerhalb von iCloud, damit nicht Gigabytes synchronisiert werden.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = "$env:LOCALAPPDATA\BaerCam\dev-venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
  python -m venv $venv
  & "$venv\Scripts\python.exe" -m pip install -e "$root\backend[dev]"
}
$env:CARGO_TARGET_DIR = "$env:LOCALAPPDATA\BaerCam\cargo-target"
Set-Location "$root\app"
if (-not (Test-Path node_modules)) { npm install }
npx tauri dev
