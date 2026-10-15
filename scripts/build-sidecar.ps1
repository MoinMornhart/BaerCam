# Baut das Python-Backend als einzelne EXE und legt sie als Tauri-Sidecar ab.
# Aufruf: powershell -File scripts/build-sidecar.ps1 [-Python <pfad\python.exe>]
param([string]$Python = "$env:LOCALAPPDATA\BaerCam\dev-venv\Scripts\python.exe")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$work = Join-Path $env:TEMP "baercam-pyinstaller"

& $Python -m PyInstaller --noconfirm --onefile --name baercam-backend `
  --distpath "$work\dist" --workpath "$work\build" --specpath $work `
  --paths "$root\backend" "$root\backend\baercam\__main__.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen" }

$triple = (rustc -Vv | Select-String "^host: (.+)$").Matches[0].Groups[1].Value
$dest = Join-Path $root "app\src-tauri\binaries"
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item "$work\dist\baercam-backend.exe" (Join-Path $dest "baercam-backend-$triple.exe") -Force
Write-Host "Sidecar fertig: $dest\baercam-backend-$triple.exe"
