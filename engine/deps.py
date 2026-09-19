"""Aggiornamento delle dipendenze Python.

`yt-dlp` invecchia in fretta (YouTube cambia spesso): qui capiamo se è ora di
riverificarlo e lo aggiorniamo con pip.

Lo stato non si basa sull'età della versione installata (che può restare la più
recente disponibile per settimane) ma sull'**ultima verifica riuscita**: se
`pip -U` va a buon fine consideriamo yt-dlp aggiornato per `CHECK_DAYS` giorni.
"""

import json
import os
import subprocess
import sys
import time

STAMP = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                     "FastDownload", "ytdlp.json")
CHECK_DAYS = 7


def version():
    """Versione di yt-dlp (es. '2026.08.19') o ''."""
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return ""


def _last_check():
    try:
        with open(STAMP, encoding="utf-8") as fh:
            return float(json.load(fh).get("checked", 0)) or None
    except Exception:
        return None


def _mark_checked():
    try:
        os.makedirs(os.path.dirname(STAMP), exist_ok=True)
        with open(STAMP, "w", encoding="utf-8") as fh:
            json.dump({"checked": time.time(), "version": version()}, fh)
    except OSError:
        pass


def stale(check_days=CHECK_DAYS):
    """True se yt-dlp non è mai stato verificato o è passato troppo tempo."""
    if not version():
        return True
    last = _last_check()
    return last is None or (time.time() - last) > check_days * 86400


def _pip(extra):
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade",
           "--disable-pip-version-check"] + extra + ["yt-dlp"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as exc:
        return False, str(exc)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    return r.returncode == 0, "\n".join(out.splitlines()[-4:])[-400:]


def update_ytdlp():
    """`pip install -U yt-dlp`. Ritorna (ok, messaggio)."""
    ok, msg = _pip([])
    if not ok and any(w in msg.lower() for w in ("permission", "denied", "access is")):
        ok, msg = _pip(["--user"])          # ambiente non scrivibile: installa per l'utente
    if ok:
        _mark_checked()                     # verifica riuscita: niente prompt per CHECK_DAYS
    return ok, msg


def auto_update(check_days=CHECK_DAYS):
    """Aggiorna se non verificato di recente. Ritorna (ok, msg) o (None,'fresh')."""
    if not stale(check_days):
        return None, "fresh"
    return update_ytdlp()


def _selftest():
    import tempfile
    global STAMP
    assert isinstance(version(), str)
    STAMP = os.path.join(tempfile.mkdtemp(prefix="fd_deps_"), "ytdlp.json")
    assert _last_check() is None
    if version():
        assert stale() is True              # mai verificato
        _mark_checked()
        assert _last_check() is not None
        assert stale() is False             # appena verificato: non datato
    print("deps selftest ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _selftest()
    else:
        ok, message = update_ytdlp()
        print(("ok" if ok else "failed") + ": " + message)
