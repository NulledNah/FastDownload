"""Stima BPM e tonalità di un brano.

Ordine delle fonti:
1. API con chiave (GetSongBPM / Songstats di stats.company) — se configurate
2. Spotify audio-features — se disponibile
3. analisi locale dell'audio (numpy) — fallback sempre disponibile

Config in %LOCALAPPDATA%\\FastDownload\\config.json:
{
  "getsongbpm_api_key": "...",
  "songstats_api_key": "...",
  "spotify_client_id": "...", "spotify_client_secret": "..."
}
"""

import base64
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

import numpy as np
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 22050
CONFIG = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                      "FastDownload", "config.json")

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
CAMELOT = {
    "C major": "8B", "C# major": "3B", "D major": "10B", "D# major": "5B",
    "E major": "12B", "F major": "7B", "F# major": "2B", "G major": "9B",
    "G# major": "4B", "A major": "11B", "A# major": "6B", "B major": "1B",
    "C minor": "5A", "C# minor": "12A", "D minor": "7A", "D# minor": "2A",
    "E minor": "9A", "F minor": "4A", "F# minor": "11A", "G minor": "6A",
    "G# minor": "1A", "A minor": "8A", "A# minor": "3A", "B minor": "10A",
}


def decode(source, seconds=120, sr=SR):
    """Decodifica i primi `seconds` secondi in mono float (ffmpeg)."""
    cmd = [FFMPEG, "-v", "error", "-i", source, "-t", str(seconds),
           "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def _stft(x, n=2048, hop=512):
    frames = 1 + (len(x) - n) // hop
    if frames < 4:
        return None, None
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    return np.abs(np.fft.rfft(x[idx] * np.hanning(n), axis=1)), hop


def estimate_bpm(x, sr=SR):
    """BPM via spettro di flusso + autocorrelazione, con prior ~120."""
    mag, hop = _stft(x)
    if mag is None:
        return 0
    flux = np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)
    flux -= flux.mean()
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    fps = sr / hop
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)
    if hi >= len(ac):
        return 0
    lags = np.arange(lo, hi)
    bpms = 60.0 * fps / lags
    prior = np.exp(-0.5 * (np.log2(bpms / 120.0) / 0.9) ** 2)
    score = ac[lo:hi] * prior
    k = int(np.argmax(score))
    lag = float(lags[k])
    if 0 < k < len(score) - 1:                    # raffinamento sub-campione
        y0, y1, y2 = score[k - 1], score[k], score[k + 1]
        denom = y0 - 2 * y1 + y2
        if denom != 0:
            lag += 0.5 * (y0 - y2) / denom
    bpm = 60.0 * fps / lag
    while bpm < 70:
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    return round(bpm, 1)


def estimate_key(x, sr=SR):
    """Tonalità via chroma + profili di Krumhansl-Schmuckler."""
    mag, hop = _stft(x, n=4096, hop=2048)
    if mag is None:
        return ""
    freqs = np.fft.rfftfreq(4096, 1 / sr)
    with np.errstate(divide="ignore", invalid="ignore"):
        midi = np.round(69 + 12 * np.log2(freqs / 440.0)).astype(int) % 12
    band = (freqs > 65) & (freqs < 2000)
    weights = mag[:, band].sum(axis=0)
    chroma = np.bincount(midi[band], weights=weights, minlength=12).astype(float)
    chroma /= (chroma.sum() + 1e-9)
    best, best_r = "", -2.0
    for i in range(12):
        for prof, mode in ((MAJOR, "major"), (MINOR, "minor")):
            r = float(np.corrcoef(np.roll(prof, i), chroma)[0, 1])
            if r > best_r:
                best_r, best = r, f"{NAMES[i]} {mode}"
    return best


def _config():
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _spotify_token(cfg):
    cid, secret = cfg.get("spotify_client_id"), cfg.get("spotify_client_secret")
    if not cid or not secret:
        return ""
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=b"grant_type=client_credentials",
        headers={"Authorization": "Basic " + auth})
    try:
        return json.load(urllib.request.urlopen(req, timeout=15)).get("access_token", "")
    except Exception:
        return ""


def spotify_info(name):
    """Metadati dal brano su Spotify (se configurato), o {}."""
    cfg = _config()
    token = _spotify_token(cfg)
    if not token:
        return {}
    query = urllib.parse.quote(name)
    req = urllib.request.Request(
        f"https://api.spotify.com/v1/search?type=track&limit=1&q={query}",
        headers={"Authorization": "Bearer " + token})
    try:
        items = json.load(urllib.request.urlopen(req, timeout=15))
        track = items["tracks"]["items"][0]
    except Exception:
        return {}
    info = {
        "spotify_title": track["name"],
        "spotify_year": (track["album"].get("release_date") or "")[:4],
        "isrc": (track.get("external_ids") or {}).get("isrc", ""),
        "src": "spotify",
    }
    # audio-features (BPM/key) è deprecato per le app nuove: se risponde, lo uso.
    try:
        req2 = urllib.request.Request(
            f"https://api.spotify.com/v1/audio-features/{track['id']}",
            headers={"Authorization": "Bearer " + token})
        af = json.load(urllib.request.urlopen(req2, timeout=15))
        if af.get("tempo"):
            info["bpm"] = round(af["tempo"], 1)
        if af.get("key") is not None and af.get("mode") is not None:
            info["key"] = f"{NAMES[af['key']]} {'major' if af['mode'] else 'minor'}"
            info["camelot"] = CAMELOT.get(info["key"], "")
    except Exception:
        pass
    return info


def _split_title(title):
    """(artista, brano) da un titolo tipo 'Artist - Song (Official Audio)'."""
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", title or "")
    text = re.sub(r"\s+", " ", text).strip()
    parts = [p.strip() for p in text.split(" - ") if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", (parts[0] if parts else "")


def _getsongbpm(artist, song, key):
    url = ("https://api.getsongbpm.com/search/?api_key=" + urllib.parse.quote(key)
           + "&type=both&lookup=song:" + urllib.parse.quote(song)
           + "&artist:" + urllib.parse.quote(artist))
    data = json.load(urllib.request.urlopen(url, timeout=15))
    hits = data.get("search") or []
    if not hits:
        return {}
    hit = hits[0]
    out = {"src": "getsongbpm"}
    if hit.get("tempo"):
        out["bpm"] = round(float(hit["tempo"]), 1)
    key_of = hit.get("key_of")
    if key_of:
        out["key"] = re.sub(r"\s*(maj|min)$", lambda m: " major" if m.group(1) == "maj" else " minor", key_of)
        out["camelot"] = CAMELOT.get(out["key"], "")
    return out


def _songstats(isrc, key):
    url = ("https://api.songstats.com/enterprise/v1/tracks/info?isrc="
           + urllib.parse.quote(isrc))
    req = urllib.request.Request(url, headers={"apikey": key})
    data = json.load(urllib.request.urlopen(req, timeout=15))
    info = data.get("track_info") or data
    out = {"src": "songstats"}
    for field in ("tempo", "bpm"):
        if info.get(field):
            out["bpm"] = round(float(info[field]), 1)
            break
    for field in ("key", "musical_key"):
        if info.get(field):
            out["key"] = str(info[field])
            out["camelot"] = CAMELOT.get(out["key"], "")
            break
    return out


def api_lookup(title, isrc=""):
    """BPM/key da API con chiave (se configurate), o {}."""
    cfg = _config()
    artist, song = _split_title(title)
    gs = cfg.get("getsongbpm_api_key")
    if gs and song:
        try:
            hit = _getsongbpm(artist, song, gs)
            if hit.get("bpm") and hit.get("key"):
                return hit
        except Exception:
            pass
    ss = cfg.get("songstats_api_key")
    if ss and isrc:
        try:
            hit = _songstats(isrc, ss)
            if hit.get("bpm") and hit.get("key"):
                return hit
        except Exception:
            pass
    return {}


def analyze(source, seconds=120):
    """BPM + tonalità (+ Camelot) dall'audio locale; metadati Spotify se configurato."""
    samples = decode(source, seconds)
    if samples.size < SR:
        return {}
    bpm = estimate_bpm(samples)
    key = estimate_key(samples)
    return {"bpm": bpm, "key": key, "camelot": CAMELOT.get(key, ""), "src": "local"}


def fast_meta(title):
    """Solo fonti rapide (Spotify/API con chiave): nessuna analisi audio."""
    info = {}
    try:
        info.update({k: v for k, v in spotify_info(title).items() if v})
    except Exception:
        pass
    try:
        for k, v in api_lookup(title, info.get("isrc", "")).items():
            if v:
                info[k] = v
    except Exception:
        pass
    return info


def meta(title, stream=""):
    """Dati del brano: fonti rapide, poi analisi locale (fallback)."""
    info = fast_meta(title)
    if not (info.get("bpm") and info.get("key")) and stream:
        try:
            local = analyze(stream, seconds=90)
            for k in ("bpm", "key", "camelot"):
                info.setdefault(k, local.get(k))
            if local.get("src") and "src" not in info:
                info["src"] = local["src"]
        except Exception:
            pass
    return info


if __name__ == "__main__":
    import sys
    print(json.dumps(analyze(sys.argv[1]), ensure_ascii=False))
