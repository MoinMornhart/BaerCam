# Stand: BärCam (Übergabe 2026-10-24)

## Was es ist
Begleit-App für **Animaze** (Holotech): steuert den Animaze-Avatar (Bär) per KI – Bewegung aus Text-Prompt, Mimik, Sprache mit eigener geklonter Stimme. Ohne Animaze (oder auf macOS/Linux) soll ein eingebauter Ersatz-Bär einspringen. In Philips Chats hieß das Projekt anfangs **„BearMe“** – BärCam ist dasselbe Projekt.

## Aktueller Stand
- **Etappe 0 (fertig):** Grundgerüst Tauri 2 + Svelte 5 (`app/`), Python-Backend als Sidecar (`backend/`, JSON-RPC über lokalen WebSocket), Installer, Update-Funktion (Tauri-Updater, signierte GitHub-Releases). Release **v0.1.0** veröffentlicht (15.10.).
- **Etappe 1 (im Code, laut README-Status aber noch „Etappe 0“):** Animaze-API-Client mit Auto-Reconnect, VMC-Sender (Körper), Programmable-Tracker-Sender (Mimik, Finger, Visemes), humanoides Skelett mit Gelenkgrenzen, Keyframe-Clips/Player, Hardware-Erkennung + Benchmark, Profile Ultra/Normal/Sparsam/Toaster, Live-Auslastung. Oberflächen: „Animaze-Verbindung“, „Avatare“, „Leistung“, „Einstellungen“.
- Noch Platzhalter in der App: „Animation erstellen“, „Meine Animationen“, „KI-Anbieter“ (Etappe 2), „Meine Stimme“ (Etappe 3).
- Ob Etappe 1 mit echtem Animaze getestet wurde: **unklar**.

## Zuletzt gemacht
- 2026-10-24 Cloud-Start-Hook (Philips Skills automatisch in Cloud-Sitzungen)
- 2026-10-15 VibeWorks-Repo-Check eingerichtet
- 2026-10-15 `pyproject.toml` nach iCloud-Konfliktkopie („pyproject 2.toml“) wiederhergestellt
- 2026-10-15 Animaze-Anbindung, Hardware-Erkennung, Leistungsprofile (Etappe 1)
- 2026-10-15 Grundgerüst, Update-Funktion

## Offen / Nächste Schritte
- **Bekannter Fehler:** GitHub-Actions „CI“ schlägt fehl – nur Job `backend (windows-latest)` bei `pytest -q` (Ubuntu/macOS/Frontend grün, zuletzt 24.10.). Ursache **unklar** (Log nicht eingesehen) → zuerst prüfen.
- README-Status von „Etappe 0“ auf Etappe 1 aktualisieren, sobald Etappe 1 bestätigt ist.
- **Etappe 2:** KI-Anbieter-Schicht (OpenAI-kompatibel inkl. kostenloser NVIDIA NIM, OpenRouter, Groq, Claude, Gemini, Ollama, LM Studio; Profile, Verbindungstest, Fallback), Prompt → Animation (LLM-Zeitachse, Text-to-Motion, Keyframes für Finger/Mimik, Selbstkorrektur, Verfeinern per Text, Cache), Render-Warteschlange, Export MP4/WebM/MOV mit Transparenz.
- **Etappe 3:** Stimm-Klon (nur eigene Stimme, Einwilligungs-Häkchen, nur lokal) + Lippensync über virtuelles Audiokabel.
- **Etappe 4:** Ersatz-Avatar (three.js/three-vrm, 2D-Variante, MediaPipe, eigene virtuelle Kamera) für ohne Animaze/macOS/Linux.
- Python- und Rust-Abhängigkeiten wurden beim Sicherheits-Scan (18.10.) nicht automatisch geprüft (Node war sauber).

## Wichtige Infos
- Technik: Tauri 2 + Svelte 5 (Oberfläche), Python ≥ 3.11 Backend (`backend/baercam/`), ONNX Runtime mit Fallback CUDA → DirectML → CoreML → CPU.
- Entwicklung: `powershell -File scripts/dev.ps1` (Oberfläche + Backend). Tests: `cd backend; pytest` und `cd app; npm run check; npm run build`.
- Release: Version in `app/package.json` erhöhen, Tag `vX.Y.Z` pushen → `.github/workflows/release.yml` baut Installer + `latest.json`. Signaturschlüssel nur lokal und als GitHub-Secret.
- Animaze-Ports (Standard): API WebSocket 9000, VMC 39539 (lokal), Programmable Tracker laut Anzeige in BärCam.
- Build-Ausgaben/venv unter `%LOCALAPPDATA%\BaerCam\…`, nicht im Projektordner.
- Grundprinzipien: läuft auf jeder Hardware (nur langsamer, nie „geht nicht“); **keine feste Animationsliste** – nirgends „unbekannte Geste → Fehler“.
- Lizenzen: Repo MIT; keine GPL-Abhängigkeiten einbinden, keine nur-nicht-kommerziellen Modelle als Standard (Clips evtl. für YouTube).
- Inhalte (Philips Vorgabe): frech erlaubt (Mittelfinger, Schimpfwörter); gesperrt: Hasssprache, sexuelle Inhalte, Nachahmen/Bloßstellen echter Personen.
- Hinweis: `CLAUDE.md` sagt noch „Projekt liegt in iCloud“ – laut Philip werden Projekte seit 18.10. nur noch lokal (`C:\Projekte`) und auf Git gespeichert.

## Philips Vorgaben
- Git-Texte (Commits, PRs, Issues, Release-Notizen) enden mit `Verfasst mit Claude 🤖` (durch Leerzeile getrennt); README hat sie als Fußzeile.
- Update-Funktion: **ja** (Tauri-Updater).
- Repo: **öffentlich** (MoinMornhart/BaerCam).
- Fortschrittsseite für Philip nach jedem Schritt aktualisieren (Link in `CLAUDE.md`).

---
Diese Datei wird beim Arbeiten aktuell gehalten: nach jedem größeren Schritt „Aktueller Stand“ und „Offen“ anpassen.
