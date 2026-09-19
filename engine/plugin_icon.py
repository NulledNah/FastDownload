"""Icona del plugin FastDownload nel Plugin database di FL Studio.

FL mostra nel Browser e nel Plugin Picker la thumbnail referenziata dal file
`<plugin>.nfo` (`Bitmap=<plugin>.png`) accanto a `<plugin>.fst`. Qui copiamo la
nostra icona arrotondata accanto a ogni FastDownload.fst presente.

Uso:  python plugin_icon.py
"""

import os
import shutil
import sys

HOME = os.path.expanduser("~")
DB_DIRS = [
    os.path.join(HOME, "Documents", "Image-Line", "FL Studio",
                 "Presets", "Plugin database"),
    os.path.join(HOME, "Documents", "Image-Line", "Data", "FL Studio",
                 "Presets", "Plugin database"),
]
ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "assets", "plugin-icon.png")
PLUGIN = "FastDownload"


def _folders():
    """Cartelle del Plugin database che contengono FastDownload.fst."""
    found = []
    for root in DB_DIRS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            if (PLUGIN + ".fst") in files:
                found.append(dirpath)
    return found


def _write_nfo(path):
    """Assicura la riga `Bitmap=FastDownload.png` preservando le altre."""
    want = "Bitmap=" + PLUGIN + ".png"
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = []
    out, seen = [], False
    for line in lines:
        if line.strip().lower().startswith("bitmap="):
            if line.strip() != want:
                out.append(want)
            else:
                out.append(line)
            seen = True
        else:
            out.append(line)
    if not seen:
        out.insert(0, want)
    text = "\n".join(out).rstrip("\n") + "\n"
    try:
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text:
                return
    except OSError:
        pass
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError:
        pass


def ensure():
    """Copia icona+nfo accanto a ogni FastDownload.fst. Ritorna i file icona scritti."""
    if not os.path.isfile(ASSET):
        return []
    try:
        data = open(ASSET, "rb").read()
    except OSError:
        return []
    written = []
    for folder in _folders():
        png = os.path.join(folder, PLUGIN + ".png")
        try:
            old = open(png, "rb").read() if os.path.isfile(png) else None
            if old != data:
                shutil.copyfile(ASSET, png)
                written.append(png)
        except OSError:
            continue
        _write_nfo(os.path.join(folder, PLUGIN + ".nfo"))
    return written


def _selftest():
    """Controlli offline su discovery e scrittura (non tocca la config di FL)."""
    import tempfile
    global DB_DIRS, ASSET
    tmp = tempfile.mkdtemp(prefix="fd_icon_")
    db = os.path.join(tmp, "db")
    folder = os.path.join(db, "Effects")
    os.makedirs(folder)
    open(os.path.join(folder, "FastDownload.fst"), "w").close()
    # nfo preesistente con altre righe: vanno preservate
    with open(os.path.join(folder, "FastDownload.nfo"), "w", encoding="utf-8") as fh:
        fh.write("Tip=keep me\n")
    ASSET = os.path.join(tmp, "icon.png")
    with open(ASSET, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\nfake")
    DB_DIRS = [db]
    assert len(_folders()) == 1
    written = ensure()
    assert written and os.path.isfile(os.path.join(folder, "FastDownload.png"))
    nfo = open(os.path.join(folder, "FastDownload.nfo"), encoding="utf-8").read()
    assert "Bitmap=FastDownload.png" in nfo and "Tip=keep me" in nfo, nfo
    assert ensure() == []                      # già aggiornato: nessuna riscrittura
    print("plugin_icon selftest ok")


def main():
    done = ensure()
    if done:
        print("icona installata accanto a FastDownload.fst:")
        for path in done:
            print("  ", path)
    else:
        print("nessun FastDownload.fst nel Plugin database di FL "
              "(aggiungi prima il plugin ai preferiti in FL).")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _selftest()
    else:
        main()
