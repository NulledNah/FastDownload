"""Logica di FastDownload: ricerca multi-sorgente, anteprima, download audio."""

import os
import json
import time
import threading
import urllib.parse
import urllib.request
import webbrowser
import concurrent.futures

import yt_dlp
import imageio_ffmpeg

try:
    import audio_meta
except Exception:                 # numpy assente: la stima BPM/key è disattivata
    audio_meta = None

try:
    import monochrome
except Exception:                 # modulo assente: la sorgente Monochrome è disattivata
    monochrome = None

try:
    import flproject
except Exception:                 # fuori da Windows: niente chiave progetto
    flproject = None

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Music", "FastDownload")
# Stato UI salvato per progetto (persistente, non volatile come il localStorage del WebView).
STATE_FILE = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                          "FastDownload", "ui_state.json")
RESULTS = 8
# ponytail: risolvi tutti i risultati insieme; tetto a 8 per non farsi rate-limitare.
PREFETCH_WORKERS = min(RESULTS, 8)

# Sorgenti di ricerca. YouTube/SoundCloud sono lossy; archive.org e Monochrome lossless.
SEARCH_SOURCES = {"youtube": "ytsearch", "soundcloud": "scsearch", "archive": None,
                  "monochrome": None}

# Disponibilità sorgente = si può SCARICARE ora? (per il grey-out "offline" nella UI)
SOURCE_TTL = 90            # secondi di cache dello stato
PROBE_TIMEOUT = 7          # timeout di rete per singola sonda
AUDIO_FORMATS = ("mp3", "flac", "wav")
LOSSLESS_EXTS = {"flac", "wav", "aiff", "aif", "ape", "alac", "wv"}
LOSSLESS_CODECS = {"flac", "alac", "pcm_s16le", "pcm_s24le", "pcm_s32le"}

# ponytail: il client android evita la sfida JS (estrazione ~2s invece di ~4s)
# e restituisce il formato 18: mp4 progressivo muxato, streammabile in <video>.
ANDROID_CLIENT = {"youtube": {"player_client": ["android"]}}
PREVIEW_FORMAT = "18/best[acodec!=none][vcodec!=none]"


def fmt_dur(seconds):
    if not seconds:
        return "--:--"
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def _config():
    path = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                        "FastDownload", "config.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _cookies():
    """Cookies del browser (config), per evitare il bot-check di YouTube."""
    browser = (_config().get("cookies_from_browser") or "").strip()
    return (browser,) if browser else None


def _extract(url, extra=None):
    opts = {"quiet": True, "no_warnings": True}
    cookies = _cookies()
    if cookies:
        opts["cookiesfrombrowser"] = cookies
    opts.update(extra or {})
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def result_from_entry(e, source):
    vid = e.get("id") or ""
    url = e.get("webpage_url") or e.get("url") or (
        f"https://www.youtube.com/watch?v={vid}" if vid else "")
    thumbs = e.get("thumbnails") or []
    return {
        "id": vid,
        "source": source,
        "title": e.get("title") or "(senza titolo)",
        "channel": e.get("uploader") or e.get("channel") or "-",
        "duration": fmt_dur(e.get("duration")),
        "url": url,
        "thumb": (thumbs[-1].get("url") if thumbs else "") or "",
    }


def _search_archive(query, n, timeout=25):
    """archive.org, solo item che contengono FLAC (lossless reale)."""
    q = urllib.parse.quote(f"({query}) AND mediatype:(audio) AND format:(FLAC)")
    url = ("https://archive.org/advancedsearch.php?q=" + q
           + "&fl[]=identifier&fl[]=title&fl[]=creator&rows=" + str(n)
           + "&page=1&output=json")
    req = urllib.request.Request(url, headers={"User-Agent": "FastDownload"})
    docs = json.load(urllib.request.urlopen(req, timeout=timeout))["response"]["docs"]
    out = []
    for doc in docs:
        ident = doc.get("identifier") or ""
        if not ident:
            continue
        out.append({
            "id": ident,
            "source": "archive",
            "title": doc.get("title") or ident,
            "channel": doc.get("creator") or "archive.org",
            "duration": "--:--",
            "url": "https://archive.org/details/" + ident,
            "thumb": "https://archive.org/services/img/" + ident,
        })
    return out


def _search_source(source, query, n):
    if source == "monochrome":
        return monochrome.search(query, n) if monochrome else []
    if source == "archive":
        return _search_archive(query, n)
    info = _extract(f"{SEARCH_SOURCES[source]}{n}:{query}", {"extract_flat": True})
    return [result_from_entry(e, source) for e in (info.get("entries") or [])]


def _probe_download(source):
    """True se la sorgente è scaricabile ora: esegue la stessa estrazione di
    download_audio (senza scaricare) su un risultato di prova."""
    try:
        if source == "monochrome":
            return bool(monochrome and monochrome.can_download())
        if source == "archive":
            items = _search_archive("music", 1, timeout=PROBE_TIMEOUT)
        else:
            info = _extract(f"{SEARCH_SOURCES[source]}1:music",
                            {"extract_flat": True, "playlistend": 1,
                             "socket_timeout": PROBE_TIMEOUT})
            items = [result_from_entry(e, source) for e in (info.get("entries") or [])]
        if not items:
            return False
        extra = {"socket_timeout": PROBE_TIMEOUT}
        if source == "youtube":
            extra["extractor_args"] = ANDROID_CLIENT      # come download_audio
        elif source == "archive":
            extra["playlist_items"] = "1"
        info = _extract(items[0].get("url", ""), extra)
        return bool(info.get("url") or info.get("formats") or info.get("entries"))
    except Exception:
        return False


def search(query, n=RESULTS, sources=None):
    """Cerca su tutte le sorgenti selezionate e unisce i risultati a rotazione."""
    chosen = [s for s in (sources or SEARCH_SOURCES) if s in SEARCH_SOURCES]
    if not chosen:
        chosen = list(SEARCH_SOURCES)
    lists = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(chosen)) as ex:
        futures = {ex.submit(_search_source, s, query, n): s for s in chosen}
        for fut in concurrent.futures.as_completed(futures):
            src = futures[fut]
            try:
                lists[src] = fut.result()
            except Exception:
                lists[src] = []
    merged = []
    depth = max((len(v) for v in lists.values()), default=0)
    for i in range(depth):
        for src in chosen:
            items = lists.get(src) or []
            if i < len(items):
                merged.append(items[i])
    return merged


def _quality_of(info):
    """Qualità reale dal formato selezionato da yt-dlp."""
    codec = (info.get("acodec") or "").split(".")[0]
    ext = (info.get("ext") or "").lower()
    abr = info.get("abr") or 0
    lossless = ext in LOSSLESS_EXTS or codec in LOSSLESS_CODECS
    if ext == "flac":
        label = "FLAC"
    elif ext == "wav":
        label = "WAV"
    else:
        label = ext.upper() if lossless else (codec or ext).upper()
    return {"codec": codec, "ext": ext, "abr": round(abr) if abr else 0,
            "lossless": lossless, "label": label}


def _error_reason(exc):
    msg = str(exc).lower()
    if "drm" in msg:
        return "drm"
    if "not available" in msg or "unavailable" in msg or "private" in msg:
        return "unavailable"
    return "error"


def _resolve_mono(track_id):
    if monochrome is None:
        return {"url": "", "quality": {}, "error": "unavailable"}
    try:
        return monochrome.stream(track_id)
    except Exception:
        return {"url": "", "quality": {}, "error": "unavailable"}


def resolve_stream(url, source="youtube", track_id=""):
    """URL per l'anteprima + qualità reale; 'error' se non riproducibile."""
    if source == "monochrome":
        return _resolve_mono(track_id or url)
    if source == "youtube":
        extra = {"extractor_args": ANDROID_CLIENT, "format": PREVIEW_FORMAT}
    elif source == "archive":
        # Un item archive può contenere più tracce (playlist): usa la prima.
        extra = {"format": "bestaudio[protocol^=http]/bestaudio/best",
                 "playlist_items": "1"}
    else:
        # SoundCloud espone gli stessi brani anche in HLS (m3u8), che <video> non
        # riproduce: preferisci sempre lo stream HTTP progressivo.
        extra = {"format": "bestaudio[protocol^=http]/bestaudio/best"}
    try:
        info = _extract(url, extra)
    except Exception as exc:
        return {"url": "", "quality": {}, "error": _error_reason(exc)}
    if not info.get("url") and info.get("entries"):
        first = next((e for e in info["entries"] if e), None)
        if first:
            info = first
    out = {"url": info.get("url") or "", "quality": _quality_of(info)}
    if not out["url"]:
        out["error"] = "unavailable"
    return out


def download_audio(url, outdir, fmt="wav", on_progress=None, source="youtube"):
    """Scarica e converte in mp3/flac/wav. Ritorna il percorso del file."""
    fmt = fmt if fmt in AUDIO_FORMATS else "wav"
    os.makedirs(outdir, exist_ok=True)

    def on_postprocess(d):
        if on_progress and d.get("status") in ("started", "processing"):
            on_progress({"status": "converting"})

    post = {"key": "FFmpegExtractAudio", "preferredcodec": fmt}
    if fmt == "mp3":
        post["preferredquality"] = "0"          # V0 (~245 kbps)
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "windowsfilenames": True,
        "ffmpeg_location": FFMPEG,
        "postprocessors": [post],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [on_progress] if on_progress else [],
        "postprocessor_hooks": [on_postprocess] if on_progress else [],
    }
    if source == "youtube":
        opts["extractor_args"] = ANDROID_CLIENT   # evita il bot-check
    elif source == "archive":
        opts["playlist_items"] = "1"              # item = album: prendi la prima traccia
    cookies = _cookies()
    if cookies:
        opts["cookiesfrombrowser"] = cookies
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.splitext(ydl.prepare_filename(info))[0] + "." + fmt


class Api:
    """Ponte fra la UI (JS) e Python."""

    def __init__(self):
        self.outdir = DEFAULT_DIR
        self._urls = {}
        self._meta = {}
        self._row_meta = {}               # BPM/tonalità rapidi, per riga dei risultati
        self._sources = None              # stato di raggiungibilità per sorgente
        self._sources_at = 0.0
        self._lock = threading.Lock()
        # ponytail: 'msg' è una chiave+parametri, tradotta lato UI (unica fonte).
        self._state = {"state": "idle", "pct": 0, "msg": {"k": "ready", "p": {}},
                       "file": "", "speed": None, "eta": None, "phase": "download"}

    @staticmethod
    def _key(vid, url, source):
        return f"{source}:{vid}" if vid else url

    def _set(self, **kw):
        with self._lock:
            self._state.update(kw)

    def search(self, query, sources=None):
        query = (query or "").strip()
        if not query:
            return []
        try:
            self._set(state="searching", pct=0, msg={"k": "searching", "p": {}})
            res = search(query, sources=sources)
            self._set(state="idle", msg={"k": "results", "p": {"n": len(res)}})
            return res
        except Exception as exc:
            self._set(state="error", msg={"k": "search_failed", "p": {"err": exc}})
            return {"error": {"k": "search_failed", "p": {"err": str(exc)}}}

    def resolve(self, vid, url, source="youtube"):
        key = self._key(vid, url, source)
        with self._lock:
            cached = self._urls.get(key)
        if cached is not None:
            return cached
        out = resolve_stream(url, source, vid)
        with self._lock:
            self._urls[key] = out          # cache anche i fallimenti (motivo in UI)
        return out

    def meta(self, vid, url, title, source="youtube"):
        """BPM/tonalità: API con chiave -> Spotify -> analisi locale (fallback)."""
        if audio_meta is None:
            return {}
        key = self._key(vid, url, source)
        with self._lock:
            if key in self._meta:
                return self._meta[key]
        stream = self.resolve(vid, url, source).get("url", "")
        try:
            info = audio_meta.meta(title, stream)
        except Exception:
            info = {}
        with self._lock:
            self._meta[key] = info
        return info

    def qualities(self, items):
        """Stato per risultato: None = in corso, {error} = non riproducibile,
        altrimenti qualità reale (codec, bitrate, lossless?)."""
        out = []
        with self._lock:
            for it in items:
                key = self._key(it.get("id"), it.get("url"),
                                it.get("source", "youtube"))
                cached = self._urls.get(key)
                if cached is None:
                    out.append(None)
                elif cached.get("error"):
                    out.append({"error": cached["error"]})
                else:
                    out.append(cached.get("quality") or None)
        return out

    def row_meta(self, items):
        """BPM/tonalità per riga: None = in corso, {} = serve analisi (nessuna fonte rapida)."""
        with self._lock:
            return [self._row_meta.get(self._key(it.get("id"), it.get("url"),
                                                 it.get("source", "youtube")))
                    for it in items]

    def prefetch(self, items):
        threading.Thread(target=self._prefetch_worker,
                         args=(list(items),), daemon=True).start()
        return {"ok": True}

    def _fast_meta(self, it):
        """BPM/tonalità da fonti rapide: inline (Monochrome) o API senza analisi."""
        if it.get("bpm"):
            info = {"bpm": it.get("bpm"), "key": it.get("key", ""),
                    "camelot": it.get("camelot", "")}
        elif audio_meta is not None:
            try:
                info = audio_meta.fast_meta(it.get("title") or "")
            except Exception:
                info = {}
        else:
            info = {}
        return {k: v for k, v in info.items() if v}

    def _prefetch_worker(self, items):
        def job(it):
            key = self._key(it.get("id"), it.get("url"), it.get("source", "youtube"))
            if key not in self._row_meta:
                info = self._fast_meta(it)
                with self._lock:
                    self._row_meta[key] = info
            if key in self._urls:
                return
            try:
                self.resolve(it.get("id"), it.get("url"),
                             it.get("source", "youtube"))
            except Exception:
                pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=PREFETCH_WORKERS) as ex:
            list(ex.map(job, items))

    def download(self, url, title, fmt="wav", vid="", source="youtube"):
        if fmt in ("flac", "wav"):
            with self._lock:
                cached = self._urls.get(self._key(vid, url, source)) or {}
            quality = cached.get("quality") or {}
            if not quality.get("lossless"):
                return {"error": {"k": "fmt_unavailable",
                                  "p": {"fmt": fmt.upper()}}}
        with self._lock:
            if self._state["state"] == "downloading":
                return {"error": {"k": "download_busy", "p": {}}}
        self._set(state="downloading", pct=0, speed=None, eta=None, phase="download",
                  msg={"k": "downloading", "p": {"title": title, "fmt": fmt}})
        threading.Thread(target=self._download_worker, args=(url, fmt, source, vid, title),
                         daemon=True).start()
        return {"ok": True}

    def _download_worker(self, url, fmt, source, vid="", title=""):
        try:
            if source == "monochrome":
                out = monochrome.download(vid, self.outdir, fmt, title, self._progress)
            else:
                out = download_audio(url, self.outdir, fmt, self._progress, source)
            self._set(state="done", pct=100, speed=None, eta=None,
                      msg={"k": "saved", "p": {"path": out}}, file=out)
        except Exception as exc:
            self._set(state="error", speed=None, eta=None,
                      msg={"k": "download_failed", "p": {"err": exc}})

    def _progress(self, d):
        """Hook yt-dlp/monochrome: bytes oppure frammenti (HLS/DASH)."""
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                pct = d.get("downloaded_bytes", 0) * 100 / total
            elif d.get("fragment_count"):
                pct = d.get("fragment_index", 0) * 100 / d["fragment_count"]
            else:
                pct = None
            speed = d.get("speed")
            self._set(phase="download", speed=speed or None, eta=d.get("eta"),
                      **({"pct": pct} if pct is not None else {}))
        elif status == "converting":
            self._set(pct=100, speed=None, eta=None, phase="convert")
        elif status == "finished":
            self._set(pct=100, speed=None, eta=0)

    def status(self):
        with self._lock:
            return dict(self._state)

    def sources_status(self, force=False):
        """Disponibilità per sorgente (True/False), con cache TTL."""
        now = time.time()
        with self._lock:
            if not force and self._sources and now - self._sources_at < SOURCE_TTL:
                return dict(self._sources)
        jobs = {name: (lambda s=name: _probe_download(s)) for name in SEARCH_SOURCES}
        result = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            futs = {ex.submit(fn): name for name, fn in jobs.items()}
            for fut in concurrent.futures.as_completed(futs):
                name = futs[fut]
                try:
                    result[name] = bool(fut.result())
                except Exception:
                    result[name] = False
        for name in jobs:
            result.setdefault(name, False)
        with self._lock:
            self._sources = result
            self._sources_at = now
        return dict(result)

    def project_info(self):
        """Stato del progetto FL corrente: {name, saved}."""
        name = ""
        if flproject is not None:
            try:
                name = flproject.project_name() or ""
            except Exception:
                name = ""
        return {"name": name, "saved": bool(name)}

    @staticmethod
    def _project_key():
        """Chiave per-progetto: nome del progetto FL, o "_default" se non rilevato."""
        if flproject is None:
            return "_default"
        try:
            return flproject.project_name() or "_default"
        except Exception:
            return "_default"

    @staticmethod
    def _load_states():
        try:
            with open(STATE_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def load_state(self):
        """Stato UI salvato per il progetto corrente (o {})."""
        with self._lock:
            return self._load_states().get(self._project_key()) or {}

    def save_state(self, state):
        """Salva lo stato UI per il progetto corrente."""
        if not isinstance(state, dict):
            return {"ok": False}
        with self._lock:
            data = self._load_states()
            data[self._project_key()] = state
            try:
                os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
                with open(STATE_FILE, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False)
            except OSError:
                return {"ok": False}
        return {"ok": True}

    def pick_folder(self):
        import webview                       # solo per l'app desktop
        res = webview.windows[0].create_file_dialog(
            webview.FOLDER_DIALOG, directory=self.outdir)
        if res:
            self.outdir = res[0]
        return self.outdir

    def open_folder(self):
        os.makedirs(self.outdir, exist_ok=True)
        os.startfile(self.outdir)
        return self.outdir

    def get_folder(self):
        return self.outdir

    def open_external(self, url):
        if url:
            webbrowser.open(url)
        return True


def selftest():
    assert fmt_dur(None) == "--:--"
    assert fmt_dur(340) == "5:40"
    assert fmt_dur(59) == "0:59"
    r = result_from_entry({"title": "T", "id": "abc", "duration": 61, "channel": "C"},
                          "youtube")
    assert r == {"id": "abc", "source": "youtube", "title": "T", "channel": "C",
                 "duration": "1:01", "url": "https://www.youtube.com/watch?v=abc",
                 "thumb": ""}, r
    assert result_from_entry({"id": "x", "uploader": "U"}, "soundcloud")["source"] == "soundcloud"
    assert Api._key("a", "u", "youtube") == "youtube:a"
    assert Api._key("", "u", "soundcloud") == "u"

    a = Api()
    a._progress({"status": "downloading", "total_bytes": 1000,
                 "downloaded_bytes": 250, "speed": 100, "eta": 8})
    assert round(a.status()["pct"]) == 25 and a.status()["eta"] == 8
    a._progress({"status": "downloading", "fragment_index": 3,
                 "fragment_count": 12})          # HLS/DASH senza total_bytes
    assert round(a.status()["pct"]) == 25
    a._progress({"status": "downloading", "downloaded_bytes": 9, "total_bytes_estimate": None})
    assert round(a.status()["pct"]) == 25         # niente fonte di pct: resta l'ultimo
    a._progress({"status": "converting"})
    assert a.status()["phase"] == "convert" and a.status()["pct"] == 100

    assert a._fast_meta({"bpm": 120, "key": "G major", "camelot": "9B"}) == \
        {"bpm": 120, "key": "G major", "camelot": "9B"}
    a._row_meta["youtube:a"] = {"bpm": 1}
    assert a.row_meta([{"id": "a", "source": "youtube"},
                       {"id": "b", "source": "youtube"}]) == [{"bpm": 1}, None]

    orig_probe = _probe_download
    globals()["_probe_download"] = lambda src: src in ("soundcloud", "archive")
    try:
        st = a.sources_status(force=True)
    finally:
        globals()["_probe_download"] = orig_probe
    assert st == {"youtube": False, "soundcloud": True, "archive": True,
                  "monochrome": False}, st

    import tempfile
    globals()["STATE_FILE"] = os.path.join(tempfile.mkdtemp(prefix="fd_state_"),
                                           "ui_state.json")
    assert a.load_state() == {}
    assert a.save_state({"query": "x", "sel": 2}) == {"ok": True}
    assert a.load_state() == {"query": "x", "sel": 2}
    assert a.save_state("nope") == {"ok": False}
    print("selftest ok")


if __name__ == "__main__":
    selftest()
