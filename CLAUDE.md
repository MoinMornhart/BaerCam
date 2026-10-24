Lies zuerst den Projektstand: @STAND.md

# BärCam – Hinweise für Claude

- Begleit-App für Animaze (Holotech). Tauri 2 + Svelte 5 in `app/`, Python-Backend in `backend/` (Sidecar, JSON-RPC über WebSocket, siehe `backend/baercam/server.py`).
- **Git-Texte:** Jede Commit-Message, jeder PR, jedes Issue und jede Release-Notiz endet mit der Zeile `Verfasst mit Claude 🤖` (durch Leerzeile getrennt). README hat sie als Fußzeile.
- **Update-Funktion:** Tauri-Updater mit signierten GitHub-Releases (`.github/workflows/release.yml`, Tag `v*`). Privater Signaturschlüssel liegt nur lokal unter `%USERPROFILE%\.tauri\baercam.key` und als GitHub-Secret – nie ins Repo.
- **Projekt liegt in iCloud.** Build-Ausgaben gehören nicht dorthin: `CARGO_TARGET_DIR=%LOCALAPPDATA%\BaerCam\cargo-target`, Dev-venv unter `%LOCALAPPDATA%\BaerCam\dev-venv`. Nach vielen Datei-Schreibvorgängen auf liegengebliebene `*.tmp.*`-Dateien und iCloud-Konfliktkopien (`name 2.ext`) prüfen – vor jedem Commit `git status` auf Umbenennungen ansehen.
- **Grundprinzipien:** läuft auf jeder Hardware (nie „geht nicht“, nur langsamer); keine feste Animationsliste – nirgends „unbekannte Geste → Fehler“.
- **Lizenzen:** Repo ist MIT. Keine GPL-Abhängigkeiten einbinden (AnimazePy, Piper nur als Referenz/separater Prozess). Keine nicht-kommerziellen Modelle als Standard (AMASS/HumanML3D-Modelle, XTTS, F5-TTS, Fish).
- Tests: `backend/` → `pytest`; `app/` → `npm run check && npm run build`.
- Fortschritts-Seite für den Nutzer: https://claude.ai/artifact/HP3UZEJaNLmCTkbnKqkzym (nach jedem Schritt aktualisieren).
