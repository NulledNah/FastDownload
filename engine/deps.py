"""Aggiornamento delle dipendenze Python.

`yt-dlp` invecchia in fretta (YouTube cambia spesso): qui capiamo se è datato e
lo aggiorniamo con pip.
"""

import datetime
import subprocess
import sys


def version():
    """Versione di yt-dlp (es. '2025.09.15') o ''."""
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return ""


def _date():
    parts = (version().split(".") + ["0", "0"])[:3]
    try:
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def stale(max_age_days=14):
    """True se yt-dlp ha più di `max_age_days` giorni (o versione illeggibile)."""
    d = _date()
    return True if d is None else (datetime.date.today() - d).days > max_age_days


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
    return ok, msg


def auto_update(max_age_days=14):
    """Aggiorna in background se datato (best effort). Ritorna (ok, msg) o (None,'fresh')."""
    if not stale(max_age_days):
        return None, "fresh"
    return update_ytdlp()


def _selftest():
    assert isinstance(version(), str)
    assert isinstance(stale(), bool)
    print("deps selftest ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _selftest()
    else:
        ok, message = update_ytdlp()
        print(("ok" if ok else "failed") + ": " + message)
