"""Individua la cartella del progetto FL Studio attivo.

FL Studio non espone il path del progetto ai plugin, quindi:
1. nome progetto dal titolo della finestra ("<progetto>.flp - FL Studio 21")
2. nome -> cartella tramite il registry di FL, la lista recenti, la cartella Projects

I risultati sono memorizzati in cache per nome progetto.
"""

import ctypes
import glob
import os
import re
import time
import winreg

FL_PROJECTS = os.path.join(os.path.expanduser("~"), "Documents",
                           "Image-Line", "FL Studio", "Projects")
RECENT_SCR = os.path.join(os.path.expanduser("~"), "Documents", "Image-Line",
                          "FL Studio", "Settings", "Browser", "Recent files.scr")
HOME = os.path.expanduser("~")
DEFAULT_ROOT = os.path.join(HOME, "Music")

_cache = {}


def _clean_name(name):
    """Toglie il marcatore di modifiche e l'estensione .flp dal nome progetto."""
    name = (name or "").strip().rstrip("*").strip()
    if name.lower().endswith(".flp"):
        name = name[:-4].strip()
    return name


def _titles():
    user32 = ctypes.windll.user32
    titles = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def visit(hwnd, _lparam):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            titles.append(buf.value)
        return True

    user32.EnumWindows(proc(visit), 0)
    return titles


def _fl_window_title():
    """Nome del progetto dal titolo della finestra di FL Studio, o ''."""
    for title in _titles():
        m = re.match(r"^(.*)[-\u2013\u2014|]\s*FL Studio", title)
        if m:
            name = _clean_name(m.group(1))
            if name and name.lower() != "fl studio":
                return name
    return ""


def _fl_running():
    return any("fl studio" in t.lower() for t in _titles())


def _recent_flp():
    """Path .flp dalla lista recenti di FL, dal piu' recente."""
    if not os.path.exists(RECENT_SCR):
        return []
    raw = open(RECENT_SCR, "rb").read()
    try:
        text = raw.decode("utf-16" if b"\x00" in raw[:200] else "utf-8", "ignore")
    except LookupError:
        return []
    return [ln.strip() for ln in text.splitlines()
            if ln.strip().lower().endswith(".flp") and os.path.exists(ln.strip())]


def _reg_value(subkey, value):
    """Valore dal primo profilo FL (per versione) che lo contiene, o ''."""
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Image-Line")
    except OSError:
        return ""
    try:
        for i in range(winreg.QueryInfoKey(root)[0]):
            name = winreg.EnumKey(root, i)
            if not name.startswith("FL Studio"):
                continue
            try:
                key = winreg.OpenKey(root, name + "\\" + subkey)
                return str(winreg.QueryValueEx(key, value)[0])
            except OSError:
                continue
    finally:
        winreg.CloseKey(root)
    return ""


def _last_project_path():
    """Ultimo path di progetto salvato da FL (registry), o ''."""
    return _reg_value(r"General\FruityLoopsMainForm", "LastProjectPath")


def _last_saved_backup():
    """Ultimo file di backup salvato da FL (registry), o ''.

    A differenza di LastProjectPath, viene aggiornato al salvataggio del progetto.
    """
    return _reg_value(r"General", "LastSavedBackup")


def project_name():
    """Nome del progetto FL attivo, o '' se non salvato/non determinabile.

    Per un progetto non salvato FL mostra solo "FL Studio 21" (senza nome):
    in quel caso torniamo '' per non puntare all'ultimo progetto salvato.
    """
    name = _fl_window_title()
    if not name or name.lower() == "untitled":
        return ""
    return name


def _debug(msg):
    """Stato dell'ultimo rilevamento, per diagnosi."""
    try:
        path = os.path.join(os.environ.get("LOCALAPPDATA") or HOME,
                            "FastDownload", "debug.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    except Exception:
        pass


def _has_flp(folder, name):
    return bool(folder) and os.path.isfile(os.path.join(folder, name + ".flp"))


def _backup_dir(path):
    """Cartella progetto da un file di backup FL (...\\<proj>\\Backup\\x.flp)."""
    if not path:
        return ""
    folder = os.path.dirname(path)
    if os.path.basename(folder).lower() == "backup":
        folder = os.path.dirname(folder)
    return folder


def _find_project_file(name, roots, depth=2):
    """Cerca <nome>.flp entro `depth` livelli dalle radici; ritorna il più recente."""
    best, best_t = "", -1.0
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        pattern = root
        for _ in range(depth + 1):
            for hit in glob.glob(os.path.join(pattern, name + ".flp")):
                try:
                    t = os.path.getmtime(hit)
                except OSError:
                    t = 0.0
                if t > best_t:
                    best, best_t = hit, t
            pattern = os.path.join(pattern, "*")
    return best


def project_dir():
    """Cartella del progetto attivo, o '' se non determinabile (con cache)."""
    name = project_name()
    titles = _titles()
    if not name:
        _debug("no project name | fl_running=%s | title=%r | registry=%r"
               % (_fl_running(),
                  next((t for t in titles if "fl studio" in t.lower()), ""),
                  _last_project_path()))
        return ""

    cached = _cache.get(name)
    if cached and time.time() - cached[1] < 60:
        return cached[0]

    folder = ""
    reg = _last_project_path().rstrip("\\/")
    backup = _last_saved_backup()
    bdir = _backup_dir(backup)

    # 1. dal registry (LastProjectPath): cartella o file, se è del progetto giusto.
    if reg:
        base = os.path.basename(reg).lower()
        if os.path.isdir(reg) and (base == name.lower() or _has_flp(reg, name)):
            folder = reg
        elif base == name.lower() + ".flp":
            folder = os.path.dirname(reg)
    # 2. lista recenti di FL
    if not folder:
        for path in _recent_flp():
            if os.path.splitext(os.path.basename(path))[0].lower() == name.lower():
                folder = os.path.dirname(path)
                break
    # 3. backup salvato di recente (LastSavedBackup) -> cartella del progetto.
    #    Aggiornato al salvataggio, a differenza di LastProjectPath.
    if not folder and _has_flp(bdir, name):
        folder = bdir
    # 4. ricerca limitata vicino alle piste note (registry/backup)
    if not folder:
        hit = _find_project_file(name, [os.path.dirname(reg), os.path.dirname(bdir)])
        if hit:
            folder = os.path.dirname(hit)
    # 5. cartella Projects di FL (ricorsiva, ultimo tentativo)
    if not folder:
        hits = glob.glob(os.path.join(FL_PROJECTS, "**", name + ".flp"),
                         recursive=True)
        folder = os.path.dirname(hits[0]) if hits else ""

    _debug("name=%r | folder=%r | registry=%r | backup=%r"
           % (name, folder, reg, backup))
    _cache[name] = (folder, time.time())
    return folder


def target_folder():
    """Cartella di download: <progetto>/FastDownload, con fallback."""
    folder = project_dir()
    return os.path.join(folder, "FastDownload") if folder \
        else os.path.join(DEFAULT_ROOT, "FastDownload")


def last_project_dir():
    """Cartella dell'ultimo progetto salvato (registry), o ''."""
    path = _last_project_path().rstrip("\\/")
    return path if path and os.path.isdir(path) else ""


if __name__ == "__main__":
    print("window title:", _fl_window_title())
    print("backup:", _last_saved_backup())
    print("recent:", _recent_flp()[:3])
    print("project:", project_dir())
    print("target:", target_folder())
