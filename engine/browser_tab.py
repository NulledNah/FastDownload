"""Tab del browser di FL Studio che punta alla cartella FastDownload.

FL riscrive le tab all'uscita di FL, quindi la tab punta a un percorso FISSO
(un junction) che viene ripuntato alla cartella del progetto attivo: la tab
non va mai riscritta e resta valida per ogni progetto.
"""

import json
import os
import subprocess
import sys

# Evita il lampo di una console quando si lanciano comandi shell da pythonw.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

TAB_NAME = "FASTDOWNLOAD"
TAB_ICON = 18              # icona "Sample"
TAB_COLOR = "$FFD2A061"    # gold (accent del tema scuro)

HOME = os.path.expanduser("~")
FL_DATA = os.path.join(HOME, "Documents", "Image-Line", "FL Studio")
TAB_DIR = os.path.join(FL_DATA, "Settings", "Browser", "UserTabs")
TAB_FILE = os.path.join(TAB_DIR, "Tab_" + TAB_NAME + ".tabconfig")
STABLE = os.path.join(FL_DATA, "FastDownload")   # percorso fisso mostrato dalla tab
# Registro dei percorsi creati, una voce per utente. L'uninstaller gira elevato
# in un altro profilo e non può ricavarli da sé: li legge da qui (area condivisa).
PUBLIC = os.environ.get("PUBLIC") or r"C:\Users\Public"
RECORD = os.path.join(PUBLIC, "FastDownload", "tabpaths.json")

TEMPLATE = """[Options]
Version=1
StateName={name}
TabType=2
Frozen=0
SortBy=0
ShowExt=0
ShowAllFiles=0
ShowOneOnly=0
Zoom=2
ShowFolderIcons=1
SortByGroup=1
OpenedOnly=0
ShowParentFolders=0
TabColor={color}
CustomTabColor=1
TabIcon={icon}
TabName={name}
ViewIndex=0
Hidden=0
ScrollerPos=0
ShowPreview=1
ShowThumbnails=1
LastTabIndex=6
FilterTags=
FilterText=
FilterExt=
TabWidth=370
TabHeight=1022
RememberTabSize=0
TabAspectCoef=0
Views=0|1|3

[Data]
DataType=0
BaseNodeType=0

[DataFolders]
Count=1
FolderName_0={folder_name}
NodePathID_0=0
NodePath_0={folder}

[Folders]
Count=2
0={folder_lower}
1={folder_lower}

"""


def tab_text(folder=STABLE):
    folder = folder.rstrip("\\/")
    return TEMPLATE.format(
        name=TAB_NAME, color=TAB_COLOR, icon=TAB_ICON,
        folder=folder, folder_lower=folder.lower(),
        folder_name=os.path.basename(folder))


def install(folder=STABLE):
    """Scrive la tab che punta a `folder`. Da eseguire con FL CHIUSO."""
    os.makedirs(TAB_DIR, exist_ok=True)
    with open(TAB_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tab_text(folder))
    _record_paths()
    return TAB_FILE


def _profile():
    return os.path.normcase(os.path.expanduser("~"))


def _load_record():
    try:
        with open(RECORD, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _record_paths():
    """Annota i percorsi di QUESTO utente senza perdere quelli degli altri."""
    data = _load_record()
    data.pop("tab", None)                     # ripulisce il vecchio formato
    data.pop("link", None)
    data[_profile()] = {"tab": TAB_FILE, "link": STABLE}
    try:
        os.makedirs(os.path.dirname(RECORD), exist_ok=True)
        with open(RECORD, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def _recorded_paths():
    """Tutti i percorsi registrati (tab, link) di tutti gli utenti."""
    data = _load_record()
    entries = [v for v in data.values() if isinstance(v, dict)]
    if isinstance(data.get("tab"), str):              # vecchio formato a utente singolo
        entries.append({"tab": data.get("tab"), "link": data.get("link")})
    out = []
    for entry in entries:
        for label in ("tab", "link"):
            if entry.get(label):
                out.append((label, entry[label]))
    return out


def _clear_record():
    try:
        os.remove(RECORD)
    except OSError:
        pass
    try:
        os.rmdir(os.path.dirname(RECORD))      # rimuove la cartella solo se vuota
    except OSError:
        pass


def _remove_path(path):
    """Rimuove un file o una junction (senza toccare la destinazione). Best effort."""
    try:
        if _is_reparse(path):
            subprocess.run(["cmd", "/c", "rmdir", path], capture_output=True,
                           creationflags=_NO_WINDOW)
            return True
        if os.path.isfile(path):
            os.remove(path)
            return True
    except OSError:
        pass
    return False


def _is_reparse(path):
    try:
        return bool(getattr(os.lstat(path), "st_reparse_tag", 0))
    except OSError:
        return False


def _exists(path):
    return os.path.exists(path) or os.path.lexists(path)


def ensure_link(target):
    """Fa puntare STABLE (junction) alla cartella del progetto attivo."""
    target = os.path.abspath(target)
    os.makedirs(target, exist_ok=True)
    try:
        if _is_reparse(STABLE) and \
                os.path.realpath(STABLE).lower() == os.path.realpath(target).lower():
            return STABLE
        if _is_reparse(STABLE):
            subprocess.run(["cmd", "/c", "rmdir", STABLE], capture_output=True,
                           creationflags=_NO_WINDOW)
        elif _exists(STABLE):
            try:
                os.rmdir(STABLE)          # rimuove solo se vuota
            except OSError:
                return None               # cartella reale non vuota: non tocco
        os.makedirs(os.path.dirname(STABLE), exist_ok=True)
        result = subprocess.run(["cmd", "/c", "mklink", "/J", STABLE, target],
                                capture_output=True, text=True,
                                creationflags=_NO_WINDOW)
        return STABLE if result.returncode == 0 else None
    except OSError:
        return None


def uninstall():
    """Rimuove tab e junction: profilo corrente + percorsi registrati.

    L'uninstaller gira elevato (profilo admin) e non può risalire al profilo
    dell'utente: i suoi percorsi li legge dal registro condiviso.
    """
    removed = []
    paths = [(TAB_FILE, "tab"), (STABLE, "junction")]
    seen = {os.path.normcase(TAB_FILE), os.path.normcase(STABLE)}
    for label, path in _recorded_paths():
        if os.path.normcase(path) not in seen:
            seen.add(os.path.normcase(path))
            paths.append((path, label))
    for path, label in paths:
        if _remove_path(path):
            removed.append(label)
    _clear_record()
    return removed


def _selftest():
    """Controlli offline su registro e rimozione (non tocca la config di FL)."""
    import tempfile
    global RECORD
    tmp = tempfile.mkdtemp(prefix="fd_tab_")
    RECORD = os.path.join(tmp, "FastDownload", "tabpaths.json")

    _record_paths()
    assert len(_recorded_paths()) == 2, _recorded_paths()     # tab + link di questo utente
    _record_paths()                                           # riscrittura: nessun duplicato
    assert len(_recorded_paths()) == 2

    data = _load_record()                                     # un altro utente si aggiunge
    data["c:\\users\\altro"] = {"tab": os.path.join(tmp, "u2.tabconfig"),
                                "link": os.path.join(tmp, "u2link")}
    with open(RECORD, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    assert len(_recorded_paths()) == 4

    with open(RECORD, "w", encoding="utf-8") as fh:           # formato vecchio (migrazione)
        json.dump({"tab": os.path.join(tmp, "old.tabconfig"),
                   "link": os.path.join(tmp, "oldlink")}, fh)
    assert len(_recorded_paths()) == 2

    f = os.path.join(tmp, "a.tabconfig")
    open(f, "w").close()
    assert _remove_path(f) and not os.path.exists(f)
    real = os.path.join(tmp, "real")
    os.makedirs(real)
    assert not _remove_path(real) and os.path.isdir(real)   # cartella vera: non si tocca
    _clear_record()
    assert not os.path.exists(RECORD) and not os.path.exists(os.path.dirname(RECORD))
    print("browser_tab selftest ok")


def main():
    if "--uninstall" in sys.argv:
        print("removed:", ", ".join(uninstall()) or "nothing")
        return
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import flproject
        project = flproject.project_dir() or flproject.last_project_dir()
    except Exception:
        project = ""
    target = os.path.join(project, "FastDownload") if project \
        else os.path.join(HOME, "Music", "FastDownload")
    print("tab      :", install(STABLE))
    print("junction :", ensure_link(target), "->", target)
    print("FL chiuso richiesto perche' la tab venga letta.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _selftest()
    else:
        main()
