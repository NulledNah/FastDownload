"""FastDownload in modalità server: serve la UI e l'API HTTP.

Usato dal plugin FL Studio (WebView2) e utilizzabile anche a mano:
    python server.py [--port 8731]

L'output di default è <cartella progetto FL>/FastDownload.
"""

import json
import os
import sys
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import api
import browser_tab
import flproject
import plugin_icon
import main as app

# Scelte manuali di cartella, ricordate per nome progetto.
STORE = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                     "FastDownload", "projects.json")

SHIM = """<script>
(function(){
  const R = (path, body) => fetch(path, {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body||{})}).then(r=>r.json());
  window.pywebview = { api: {
    get_folder: ()=> fetch('/api/folder').then(r=>r.json()).then(d=>d.folder),
    search: (q, sources) => R('/api/search', {q, sources}),
    resolve: (id, url, source) => R('/api/resolve', {id, url, source}),
    meta: (id, url, title, source) => R('/api/meta', {id, url, title, source}),
    qualities: items => R('/api/qualities', {items}),
    row_meta: items => R('/api/row_meta', {items}),
    prefetch: items => R('/api/prefetch', {items}),
    download: (id, url, source, title, fmt) => R('/api/download', {id, url, source, title, fmt}),
    status: ()=> R('/api/status'),
    sources_status: ()=> R('/api/sources_status'),
    project_info: ()=> R('/api/project_info'),
    save_state: state => R('/api/save_state', {state}),
    load_state: ()=> R('/api/load_state'),
    pick_folder: ()=> R('/api/pick_folder').then(d=>d.folder),
    open_folder: ()=> R('/api/open_folder'),
    open_external: url => R('/api/open_external', {url})
  }};
  window.dispatchEvent(new Event('pywebviewready'));
})();
</script>"""


class Bridge:
    def __init__(self):
        self.api = api.Api()
        self.overrides = self._load()

    def _load(self):
        try:
            with open(STORE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(STORE), exist_ok=True)
            with open(STORE, "w", encoding="utf-8") as fh:
                json.dump(self.overrides, fh, indent=2)
        except Exception:
            pass

    @staticmethod
    def _key():
        """Chiave override: nome progetto, o ripiego per i progetti senza nome."""
        return flproject.project_name() or "_default"

    def folder(self):
        """Cartella corrente: scelta manuale (progetto o ripiego), altrimenti rilevata."""
        override = self.overrides.get(self._key())
        self.api.outdir = override or flproject.target_folder()
        browser_tab.ensure_link(self.api.outdir)
        return self.api.outdir

    def set_folder(self, folder):
        self.overrides[self._key()] = folder
        self._save()
        self.api.outdir = folder

    def page(self):
        html = app.build_html()
        return html.replace("</body>", SHIM + "</body>").encode("utf-8")


def make_handler(bridge):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj).encode("utf-8"))

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, bridge.page(), "text/html; charset=utf-8")
            elif self.path == "/api/folder":
                self._json({"folder": bridge.folder()})
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                data = {}
            a = bridge.api
            route = self.path
            if route == "/api/search":
                self._json(a.search(data.get("q", ""), data.get("sources")))
            elif route == "/api/resolve":
                self._json(a.resolve(data.get("id", ""), data.get("url", ""),
                                     data.get("source", "youtube")))
            elif route == "/api/prefetch":
                self._json(a.prefetch(data.get("items", [])))
            elif route == "/api/qualities":
                self._json(a.qualities(data.get("items", [])))
            elif route == "/api/row_meta":
                self._json(a.row_meta(data.get("items", [])))
            elif route == "/api/meta":
                self._json(a.meta(data.get("id", ""), data.get("url", ""),
                                  data.get("title", ""), data.get("source", "youtube")))
            elif route == "/api/download":
                a.outdir = bridge.folder()
                self._json(a.download(data.get("url", ""), data.get("title", ""),
                                      data.get("fmt", "wav"), data.get("id", ""),
                                      data.get("source", "youtube")))
            elif route == "/api/status":
                self._json(a.status())
            elif route == "/api/sources_status":
                self._json(a.sources_status())
            elif route == "/api/project_info":
                self._json(a.project_info())
            elif route == "/api/save_state":
                self._json(a.save_state(data.get("state") or {}))
            elif route == "/api/load_state":
                self._json(a.load_state())
            elif route == "/api/pick_folder":
                folder = pick_folder(bridge.folder())
                if folder:
                    bridge.set_folder(folder)
                self._json({"folder": bridge.folder()})
            elif route == "/api/open_folder":
                a.open_folder()
                self._json({"ok": True})
            elif route == "/api/open_external":
                a.open_external(data.get("url", ""))
                self._json({"ok": True})
            else:
                self._send(404, b"not found", "text/plain")

    return Handler


def pick_folder(initial):
    """Dialog nativo Windows di scelta cartella.

    ctypes/Shell32 invece di tkinter: funziona dal thread HTTP (che non ha un
    loop Tk) e si apre in primo piano sulla finestra attiva.
    """
    try:
        import ctypes
        from ctypes import wintypes

        class BROWSEINFOW(ctypes.Structure):
            _fields_ = [("hwndOwner", wintypes.HWND),
                        ("pidlRoot", ctypes.c_void_p),
                        ("pszDisplayName", wintypes.LPWSTR),
                        ("lpszTitle", wintypes.LPCWSTR),
                        ("ulFlags", wintypes.UINT),
                        ("lpfn", ctypes.c_void_p),
                        ("lParam", wintypes.LPARAM),
                        ("iImage", ctypes.c_int)]

        shell32, ole32, user32 = (ctypes.windll.shell32, ctypes.windll.ole32,
                                  ctypes.windll.user32)
        shell32.SHBrowseForFolderW.argtypes = [ctypes.POINTER(BROWSEINFOW)]
        shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
        shell32.SHGetPathFromIDListW.argtypes = [ctypes.c_void_p, wintypes.LPWSTR]
        shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
        shell32.SHParseDisplayName.argtypes = [
            wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        shell32.SHParseDisplayName.restype = ctypes.c_long
        ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        user32.GetForegroundWindow.restype = wintypes.HWND

        ole32.CoInitializeEx(None, 2)          # COINIT_APARTMENTTHREADED
        root = ctypes.c_void_p()
        try:
            if initial and os.path.isdir(initial):
                if shell32.SHParseDisplayName(initial, None,
                                              ctypes.byref(root), 0, None) == 0:
                    root = ctypes.c_void_p(root.value)   # PIDL della cartella iniziale
                else:
                    root = ctypes.c_void_p()
            name = ctypes.create_unicode_buffer(260)
            bi = BROWSEINFOW()
            bi.hwndOwner = user32.GetForegroundWindow()
            bi.pidlRoot = root
            bi.pszDisplayName = ctypes.cast(name, wintypes.LPWSTR)
            bi.lpszTitle = "FastDownload"
            # RETURNONLYFSDIRS | EDITBOX | NEWDIALOGSTYLE
            bi.ulFlags = 0x0001 | 0x0010 | 0x0040
            pidl = shell32.SHBrowseForFolderW(ctypes.byref(bi))
            if not pidl:
                return ""
            path = ctypes.create_unicode_buffer(260)
            ok = shell32.SHGetPathFromIDListW(pidl, path)
            ole32.CoTaskMemFree(pidl)
            return path.value if ok else ""
        finally:
            if root:
                ole32.CoTaskMemFree(root)
            ole32.CoUninitialize()
    except Exception:
        return ""


def serve(port):
    bridge = Bridge()
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(bridge))
    srv.daemon_threads = True
    browser_tab.install()          # tab del browser (ha effetto a FL chiuso)
    plugin_icon.ensure()           # icona del plugin accanto a FastDownload.fst
    print(f"FastDownload server: http://127.0.0.1:{port}/", flush=True)
    print(f"project folder: {flproject.project_dir() or '(not detected)'}", flush=True)
    print(f"output: {bridge.folder()}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8731)
    args = parser.parse_args()
    try:
        serve(args.port)
    except OSError as exc:
        print(f"port {args.port} unavailable: {exc}", file=sys.stderr)
        sys.exit(1)
