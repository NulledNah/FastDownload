"""Sorgente Monochrome: stessa rete di istanze hifi-api usata da monochrome.tf.

Le istanze tengono loro le credenziali Tidal, quindi nessun account è richiesto:
basta che almeno una risponda. La qualità massima è HI_RES_LOSSLESS (FLAC
24 bit); se non disponibile si scende a LOSSLESS (FLAC 16/44.1).

Config in %LOCALAPPDATA%\\FastDownload\\config.json (opzionale):
    {
      "monochrome_instances": ["https://mia-istanza"],   # provate per prime
      "monochrome_country": "IT"                          # default US
    }
"""

import base64
import concurrent.futures
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

import imageio_ffmpeg

try:
    import audio_meta as _audio_meta      # per Camelot dai dati di ricerca
except Exception:
    _audio_meta = None

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FastDownload"
DEAD_TTL = 60          # secondi in cui un host fallito viene saltato
CHUNK = 512 * 1024

DEFAULT_INSTANCES = [
    "https://eu-central.monochrome.tf",
    "https://us-west.monochrome.tf",
    "https://arran.monochrome.tf",
    "https://api.monochrome.tf",
    "https://monochrome-api.samidy.com",
    "https://triton.squid.wtf",
    "https://wolf.qqdl.site",
    "https://maus.qqdl.site",
    "https://vogel.qqdl.site",
    "https://hund.qqdl.site",
    "https://tidal.kinoplus.online",
    "https://hifi.p1nkhamster.xyz",
]

CONFIG = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                      "FastDownload", "config.json")
_dead = {}                       # base -> timestamp fino a cui saltarla
_active = {"base": None}         # ultima istanza che ha risposto


def _config():
    try:
        with open(CONFIG, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _instances():
    user = _config().get("monochrome_instances") or []
    seen, out = set(), []
    for base in list(user) + DEFAULT_INSTANCES:
        base = (base or "").rstrip("/")
        if base and base not in seen:
            seen.add(base)
            out.append(base)
    return out


def _fetch(base, path, params=None, timeout=20):
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict) or data.get("data") is None:
        raise ValueError("risposta non valida")
    return data["data"]


def _fanout(candidates, path, params, timeout):
    """Interroga le istanze in parallelo; vince la prima che risponde."""
    last = {"err": None}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(candidates))
    futures = {pool.submit(_fetch, base, path, params, timeout): base
               for base in candidates}

    def note(fut, base):
        try:
            fut.result()
        except Exception as exc:
            _dead[base] = time.time() + DEAD_TTL
            last["err"] = exc

    for fut, base in futures.items():
        fut.add_done_callback(lambda f, b=base: note(f, b))
    try:
        for fut in concurrent.futures.as_completed(futures, timeout=timeout + 2):
            try:
                data = fut.result()
            except Exception:
                continue
            _active["base"] = futures[fut]
            return data
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    raise last["err"] or RuntimeError("nessuna istanza disponibile")


def _get(path, params=None, timeout=15):
    """Usa l'istanza attiva; altrimenti prova tutte in parallelo (failover)."""
    base = _active["base"]
    if base and _dead.get(base, 0) <= time.time():
        try:
            return _fetch(base, path, params, timeout)
        except Exception as exc:
            _dead[base] = time.time() + DEAD_TTL
            _active["base"] = None
            last = exc
    else:
        last = None
    candidates = [b for b in _instances() if _dead.get(b, 0) <= time.time()]
    if not candidates:
        raise last or RuntimeError("nessuna istanza disponibile")
    return _fanout(candidates, path, params, timeout)


def _fmt_dur(seconds):
    if not seconds:
        return "--:--"
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


_FLATS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#",
          "Cb": "B", "Fb": "E"}


def key_label(key, scale):
    """'Ab' + 'MAJOR' -> 'G# major' (nomi diesis, compatibili con Camelot)."""
    if not key:
        return ""
    key = _FLATS.get(key, key)
    return f"{key} {(scale or '').lower()}".strip()


def _camelot(label):
    return _audio_meta.CAMELOT.get(label, "") if (_audio_meta and label) else ""


def search(query, n=8):
    data = _get("/search/", {"s": query, "limit": int(n)})
    out = []
    for e in (data.get("items") or [])[:n]:   # alcune istanze ignorano `limit`
        cover = (e.get("album") or {}).get("cover") or ""
        label = key_label(e.get("key"), e.get("keyScale"))
        out.append({
            "id": str(e.get("id") or ""),
            "source": "monochrome",
            "title": e.get("title") or "(senza titolo)",
            "channel": (e.get("artist") or {}).get("name") or "-",
            "duration": _fmt_dur(e.get("duration")),
            "url": e.get("url") or f"https://tidal.com/browse/track/{e.get('id')}",
            "thumb": ("https://resources.tidal.com/images/"
                      + cover.replace("-", "/") + "/320x320.jpg") if cover else "",
            "bpm": e.get("bpm") or "",
            "key": label,
            "camelot": _camelot(label),
        })
    return out


def _quality(data):
    depth = data.get("bitDepth")
    rate = data.get("sampleRate")
    hires = (data.get("audioQuality") == "HI_RES_LOSSLESS") or (depth and depth > 16)
    label = "FLAC"
    if hires:
        label = f"FLAC {depth}bit/{round(rate / 1000)}k" if depth and rate else "FLAC Hi-Res"
    return {"codec": "flac", "ext": "flac", "abr": 0, "lossless": True, "label": label}


def _manifest(data, mime):
    raw = base64.b64decode(data.get("manifest") or b"")
    if "bts" in mime:
        info = json.loads(raw)
        if info.get("encryptionType") not in (None, "NONE"):
            raise ValueError("manifest cifrato")
        urls = info.get("urls") or []
        return ("url", urls[0]) if urls else ("none", None)
    if "dash" in mime:
        return ("mpd", raw)
    return ("none", None)


def stream(track_id):
    """Anteprima (se diretta) + qualità. url vuota = solo download."""
    data = _get("/track/", {"id": track_id, "quality": "HI_RES_LOSSLESS"}, timeout=30)
    kind, payload = _manifest(data, (data.get("manifestMimeType") or "").lower())
    url = payload if kind == "url" else ""
    return {"url": url, "quality": _quality(data)}


def can_download(track_id=""):
    """True se /track/ restituisce un manifest scaricabile (bts o DASH)."""
    if not track_id:
        try:
            items = search("music", 1)
            track_id = items[0]["id"] if items else ""
        except Exception:
            return False
    if not track_id:
        return False
    try:
        data = _get("/track/", {"id": track_id, "quality": "HI_RES_LOSSLESS"},
                    timeout=15)
        kind, _ = _manifest(data, (data.get("manifestMimeType") or "").lower())
        return kind in ("url", "mpd")
    except Exception:
        return False


def _safe_name(title):
    name = re.sub(r'[<>:"/\\|?*]', "_", title or "track").strip().rstrip(". ")
    return name[:150] or "track"


def _rm(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _fetch_file(url, dest, on_progress):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        done, start = 0, time.time()
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if on_progress:
                speed = done / max(time.time() - start, 0.001)
                eta = int((total - done) / speed) if total and speed else None
                on_progress({"status": "downloading", "downloaded_bytes": done,
                             "total_bytes": total or None, "speed": speed, "eta": eta})
    if on_progress:
        on_progress({"status": "finished"})


def _transcode(src, dest, fmt):
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-v", "error",
           "-protocol_whitelist", "file,http,https,tcp,tls,crypto", "-i", src]
    if fmt == "flac":
        cmd += ["-c:a", "flac"]
    elif fmt == "wav":
        cmd += ["-c:a", "pcm_s16le"]
    elif fmt == "mp3":
        cmd += ["-q:a", "0"]
    cmd += [dest]
    subprocess.run(cmd, check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def download(track_id, outdir, fmt="flac", title="", on_progress=None):
    """Scarica in flac/wav/mp3. Ritorna il percorso del file."""
    fmt = fmt if fmt in ("flac", "wav", "mp3") else "flac"
    data = _get("/track/", {"id": track_id, "quality": "HI_RES_LOSSLESS"}, timeout=30)
    kind, payload = _manifest(data, (data.get("manifestMimeType") or "").lower())
    if kind == "none":
        raise ValueError("traccia non disponibile")
    os.makedirs(outdir, exist_ok=True)
    name = _safe_name(title)
    final = os.path.join(outdir, name + "." + fmt)

    if kind == "url":
        if fmt == "flac":
            _fetch_file(payload, final, on_progress)
            return final
        tmp = os.path.join(outdir, name + ".tmp.flac")
        try:
            _fetch_file(payload, tmp, on_progress)
            _transcode(tmp, final, fmt)
        finally:
            _rm(tmp)
        return final

    mpd = os.path.join(outdir, name + ".tmp.mpd")
    try:
        with open(mpd, "wb") as fh:
            fh.write(payload)
        _transcode(mpd, final, fmt)
    finally:
        _rm(mpd)
    if on_progress:
        on_progress({"status": "finished"})
    return final


def _selftest():
    """Decodifica manifest bts e MPD senza rete."""
    bts = base64.b64encode(json.dumps({
        "mimeType": "audio/flac", "codecs": "flac", "encryptionType": "NONE",
        "urls": ["https://example.com/a.flac"],
    }).encode()).decode()
    assert _manifest({"manifest": bts}, "application/vnd.tidal.bts") == \
        ("url", "https://example.com/a.flac")
    mpd = base64.b64encode(b"<MPD><BaseURL>x</BaseURL></MPD>").decode()
    kind, payload = _manifest({"manifest": mpd}, "application/dash+xml")
    assert kind == "mpd" and payload.startswith(b"<MPD>")
    assert _quality({"audioQuality": "HI_RES_LOSSLESS", "bitDepth": 24,
                     "sampleRate": 96000})["label"] == "FLAC 24bit/96k"
    assert _quality({"audioQuality": "LOSSLESS", "bitDepth": 16,
                     "sampleRate": 44100})["label"] == "FLAC"
    assert _safe_name("AC/DC: Back?") == "AC_DC_ Back_"

    orig_get = _get
    try:
        globals()["_get"] = lambda *a, **k: {"manifest": bts,
            "manifestMimeType": "application/vnd.tidal.bts"}
        assert can_download("1") is True
        globals()["_get"] = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        assert can_download("1") is False
    finally:
        globals()["_get"] = orig_get
    print("monochrome selftest ok")


if __name__ == "__main__":
    _selftest()
