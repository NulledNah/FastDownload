"""FastDownload - cerca, guarda e scarica tracce audio in WAV da YouTube.

Avvio:  python main.py
Test:   python main.py --test
"""

import pathlib
import sys

import webview

from api import Api, selftest

UI_DIR = pathlib.Path(__file__).resolve().parent / "ui"


def build_html():
    """Compone la pagina unendo index.html, styles.css e app.js (nessun server)."""
    def read(name):
        return (UI_DIR / name).read_text(encoding="utf-8")

    return (read("index.html")
            .replace("/*__STYLES__*/", read("styles.css"))
            .replace("/*__SCRIPT__*/", read("app.js")))


def main():
    webview.create_window(
        "FastDownload", html=build_html(), js_api=Api(),
        width=1120, height=740, min_size=(900, 600),
        background_color="#F5EAD6",
    )
    webview.start()


if __name__ == "__main__":
    if "--test" in sys.argv:
        selftest()
    else:
        main()
