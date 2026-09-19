# Changelog

## v1.0.1

Maintenance and safety release.

- **yt-dlp auto-update**: the app refreshes `yt-dlp` (via pip) when it hasn't been
  checked recently, and shows an **Update yt-dlp** button only when needed.
  The staleness check now uses the *last successful update* instead of the version
  date, which previously kept nagging when the installed version was already the latest.
- **CSRF guard**: the local API now requires a per-run token, so a web page can no
  longer POST to `127.0.0.1:8731` (e.g. trigger a download or open a folder).
  The UI sends the token automatically.
- Removed a dead single-user migration branch in the browser-tab record.
- Added `TODO.md`.

Asset: `FastDownload-Setup.exe` (v1.0.1) — SHA-256
`98795D05057F17345C0F41DB806C6590F7E01903B67022FED244C3658A20ACB6`

Requirements and installation: see v1.0.0 below.

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
