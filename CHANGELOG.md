# Changelog

## v1.0.0 — first release

**FastDownload** searches multiple sources, previews tracks and downloads them as
**MP3 / FLAC / WAV** into your FL Studio project folder. Ships as a VST3 plugin,
a standalone app and a desktop app, plus a browser tab inside FL Studio.

### Highlights

- **Multi-source search**: YouTube, SoundCloud, archive.org (real FLAC) and
  Monochrome (Tidal/FLAC via public HiFi API instances).
- **Preview player** — playback starts only when you press play.
- **Downloads** MP3 / FLAC / WAV with progress %, speed and ETA; FLAC/WAV enabled
  only for lossless sources.
- **Per-row info**: audio quality pills and, when quickly available, BPM / key /
  Camelot (otherwise a hint).
- **Sort** by search relevance, audio quality (high↔low) or duration (short↔long).
- **Project-aware folder**: downloads go to `<FL project>\FastDownload`; unsaved
  projects use a default folder with a "save the project" warning.
- **Per-project UI state** restored when reopening the plugin in the same project.
- **FL Studio browser tab** (`FASTDOWNLOAD`) and **plugin icon** in the Browser / Plugin Picker.
- **Light/dark theme** (dark by default) and **English / Italian** UI.
- **Per-source offline detection** with a badge and periodic re-check.

### Requirements

- Windows 10/11 (x64)
- Python 3.10+ (with `pip` on PATH)
- FL Studio 21+ (only for the VST3 plugin)

### Install

1. Download `FastDownload-Setup.exe` below.
2. Run it (administrator). It installs the engine, the VST3, the Python
   dependencies, the optional FL browser tab and the plugin icon.
3. In FL Studio: *Options → Manage plugins → Find more plugins*, then add
   **FastDownload** to a **mixer insert** (Fx).

### Asset

- `FastDownload-Setup.exe` (v1.0.0)
- SHA-256: `4A4913988D975FB379ECD02896F08F8A2D9C81989297B3A87107666BF4F50281`

### Notes

- The **Monochrome** source needs at least one reachable HiFi API instance; it may
  show as **offline** when the public instances are down.
- FastDownload is a personal-use tool: respect copyright and the terms of service
  of every source you use.
