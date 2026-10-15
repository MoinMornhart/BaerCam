# 🐻 BärCam

**BärCam** ist eine Begleit-App für [Animaze](https://www.animaze.us/) (Holotech Studios). Sie steuert deinen Animaze-Avatar per KI: Du beschreibst eine Bewegung in Worten, BärCam erzeugt daraus Animation, Mimik und Sprache – mit deiner eigenen, geklonten Stimme. Ohne Animaze (oder auf macOS/Linux) springt ein eingebauter Ersatz-Bär ein.

> Status: **Etappe 0 – Grundgerüst.** Die Bereiche sind angelegt, die Funktionen folgen etappenweise (siehe unten).

## Installation (Windows)

1. Unter [Releases](https://github.com/MoinMornhart/BaerCam/releases) die Datei `BärCam_<version>_x64-setup.exe` laden und starten.
2. BärCam aktualisiert sich selbst: **Einstellungen → „Nach Updates suchen“**.

## Animaze vorbereiten

### Animaze API einschalten (für Avatare, Emotes, Posen, virtuelle Kamera)
1. Animaze öffnen → **Settings → Animaze API**.
2. **Enabled** einschalten. Port bleibt standardmäßig **9000** (in BärCam änderbar).

### VMC-Empfang einschalten (für Körperbewegungen)
1. In Animaze: **Settings → Advanced Tracking Configuration → Select Trackers → VMC Body Tracker**.
2. IP prüfen (lokal `127.0.0.1`), Port **39539**, dann **Connect**.

### Programmable Tracker (für Mimik, Finger, Lippensync)
1. In Animaze unter den Trackern den **Programmable Tracker** aktivieren.
2. IP und Port eintragen, die BärCam unter „Animaze-Verbindung“ anzeigt.

### Lippensync über virtuelles Kabel
BärCam schickt die Stimme über ein virtuelles Audiogerät (z. B. [VB-Audio Virtual Cable](https://vb-audio.com/Cable/), Donationware) an Animaze. In Animaze das Mikrofon auf **CABLE Output** stellen. BärCam hilft bei der Einrichtung.

## Entwicklung

Voraussetzungen: Node.js 22+, Rust (stable, MSVC), Python 3.11+, unter Windows die *Visual Studio Build Tools* (C++).

```powershell
powershell -File scripts/dev.ps1      # startet Oberfläche + Backend
cd backend; pytest                    # Backend-Tests
cd app; npm run check; npm run build  # Oberfläche prüfen
```

Release: Version in `app/package.json` erhöhen, Tag `vX.Y.Z` pushen – GitHub Actions baut den Installer und das Update.

## Aufbau

| Teil | Technik | Warum |
|---|---|---|
| Oberfläche | Tauri 2 + Svelte 5 | Nutzt die System-WebView statt eines eigenen Chromiums → viel weniger RAM als Electron; eingebauter, signierter Updater |
| Backend | Python (Sidecar), JSON-RPC über lokalen WebSocket | KI-Ökosystem (ONNX Runtime, Audio, Motion) ist in Python zuhause |
| KI | ONNX Runtime: CUDA → DirectML → CoreML → CPU | Läuft auf jeder Hardware, nur unterschiedlich schnell |
| Animaze | WebSocket-API, VMC (OSC), Programmable Tracker (UDP) | Offizielle Schnittstellen |

## Etappen

0. Grundgerüst, Installer, Update-Funktion
1. Animaze-Verbindung (API + VMC + Programmable Tracker), Hardware-Erkennung, Leistungsprofile
2. KI-Anbieter-Schicht, Prompt → Animation, Render-Warteschlange
3. Stimm-Klon + Lippensync
4. Ersatz-Avatar (ohne Animaze, macOS, Linux)

## Lizenz

MIT – siehe [LICENSE](LICENSE). Hinweise zu Modell-Lizenzen stehen in der App bei jedem Modell.

---

Verfasst mit Claude 🤖
