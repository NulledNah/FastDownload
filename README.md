# FastDownload

**Search, preview and download audio in MP3, FLAC or WAV — right inside FL Studio.**

FastDownload is a small music tool that searches multiple sources, previews tracks, and
saves them (converted to MP3 / FLAC / WAV) into your **FL Studio project folder**.
It ships as a **VST3 plugin**, a **standalone app** and a **desktop app**, plus a
one-click browser tab inside FL Studio.

> **In breve (IT):** cerca su più fonti, ascolta l'anteprima e scarica in MP3/FLAC/WAV
> direttamente nella cartella del progetto FL. Plugin VST3 + standalone + app desktop,
> con tab dedicata nel browser di FL Studio.

---

## Features

- **Multi-source search**: YouTube, SoundCloud, archive.org (real FLAC) and Monochrome (Tidal via HiFi API instances).
- **Preview player** with quality/buffering feedback — playback starts when *you* press play.
- **Download** as **WAV / FLAC / MP3**, with progress %, speed and ETA; FLAC/WAV are enabled only for lossless sources.
- **Per-row info**: audio quality and, when quickly available, **BPM / key / Camelot** (otherwise a hint to get more info).
- **Sort results** by search relevance, audio quality (high↔low) or duration (short↔long).
- **Project-aware output folder**: downloads always land in `<your FL project folder>\FastDownload`. Unsaved projects use a default folder, with a warning asking you to save.
- **Per-project UI state**: query, results, source, sort and format are restored when you reopen the plugin in the same project.
- **FL Studio browser tab** (`FASTDOWNLOAD`) pointing at the active project's folder.
- **Plugin icon** in the FL Browser / Plugin Picker.
- **Light / dark theme** (dark by default) and **English / Italian** UI.
- **Offline detection** per source with a "offline" badge and periodic re-check.

## Requirements

- **Windows 10/11 (x64)**
- **Python 3.10+** with `pip` on PATH — used by the engine (the plugin launches it).
- **FL Studio 21+** for the VST3 plugin (the standalone/desktop app work without FL).
- Internet connection.

## Install (Windows)

1. Download **`FastDownload-Setup.exe`** from the [Releases](../../releases) page.
2. Run it (administrator). It will:
   - install the Python engine to `Program Files\FastDownload`,
   - install the VST3 to `C:\Program Files\Common Files\VST3`,
   - write the engine path to `HKLM\Software\FastDownload`,
   - install Python dependencies (`yt-dlp`, `imageio-ffmpeg`, `pywebview`, `numpy`),
   - optionally add the **FASTDOWNLOAD** tab to the FL Studio browser (FL must be closed),
   - install the plugin icon into the FL Plugin database.
3. In FL Studio: **Options → Manage plugins → Find more plugins**, then add
   **FastDownload** to a **mixer insert** (it is an effect/Fx).

> Skip the "browser tab" task if FL Studio is open; you can add it later from
> `FastDownload.bat` → *Install browser tab into FL*.

## Using it in FL Studio

- Add **FastDownload** on a **mixer insert slot** (Fx), not the Channel Rack.
- The plugin serves its UI from a local Python server it starts automatically
  (`http://127.0.0.1:8731`).
- Pick a **source**, search, click a result to preview (press play), choose a
  format and hit **Download**.
- Files are written to `…\<project>\FastDownload`; the `FASTDOWNLOAD` browser tab
  points to the same folder (it uses a junction that is re-pointed automatically).

### Desktop / standalone

- **Desktop app**: `FastDownload.bat` → *Desktop app*, or `python engine\main.py`.
- **Standalone plugin**: `FastDownload.bat` → *Plugin standalone* (needs a build).
- **Server only**: `python engine\server.py --port 8731`.

## Sources

| Source | Notes |
|---|---|
| YouTube | Lossy; preview via progressive stream. |
| SoundCloud | Lossy. |
| archive.org | Lossless when the item contains FLAC. |
| Monochrome | FLAC (up to 24-bit) via public HiFi API instances; depends on their availability. |

> The Monochrome source holds the credentials on the server side, so **no Tidal
> account is required**; it only needs at least one reachable instance.

## Configuration

Optional settings live in `%LOCALAPPDATA%\FastDownload\config.json`:

```json
{
  "cookies_from_browser": "chrome",
  "spotify_client_id": "…",
  "spotify_client_secret": "…",
  "getsongbpm_api_key": "…",
  "songstats_api_key": "…",
  "monochrome_country": "US",
  "monochrome_instances": ["https://your-instance.example"]
}
```

- `cookies_from_browser` — pass browser cookies to yt-dlp (helps with YouTube bot checks).
- `spotify_*`, `getsongbpm_api_key`, `songstats_api_key` — fast BPM/key lookups (otherwise local analysis is used on selection).
- `monochrome_instances` — extra/own HiFi API instances, tried first.

Local data (all under `%LOCALAPPDATA%\FastDownload`): `config.json`, `projects.json`
(manual folders per project), `ui_state.json` (per-project UI state), `debug.log`.

## Building from source

Prerequisites: **Visual Studio 2022** (C++ desktop), **CMake ≥ 3.22**.

```bat
FastDownload.bat        :: then choose 4  -> Build plugin VST3
```

The build script downloads **JUCE 8.0.15** and the **WebView2 SDK** into
`plugin\external`, configures CMake, builds, and copies artifacts to `plugin\dist`.
Install the plugin system-wide with `FastDownload.bat` → *5* (admin).

To build the installer you need [Inno Setup](https://jrsoftware.org/isdl.php):
`FastDownload.bat` → *7*.

## Credits

- [JUCE](https://juce.com/) — plugin framework.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — media extraction.
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — bundled FFmpeg.
- [pywebview](https://pywebview.flowrl.com/) — desktop UI.
- [Monochrome](https://github.com/monochrome-music/monochrome) and the HiFi API
  instance ecosystem — Tidal search/download used by the Monochrome source.

## License

**GNU General Public License v3.0** — see [LICENSE](LICENSE).
The plugin links JUCE under its GPL option, so the project is distributed under the GPL.

## Disclaimer

FastDownload is a personal-use tool. It only fetches what the selected sources
already expose publicly. **Respect copyright and the terms of service of every
source** you use. The authors are not responsible for how you use it.
