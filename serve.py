#!/usr/bin/env python3
"""Serve the site locally and open it.

Needed because the page fetches one JSON file per company, and browsers block
fetch() on file:// URLs for security reasons. On GitHub Pages the site is served
over HTTP already, so this is only for local preview.

    python serve.py
"""

import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path

PORT = 8765
SITE = Path(__file__).resolve().parent / "site"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def log_message(self, *a):  # keep the console quiet
        pass


def main() -> None:
    if not (SITE / "data.js").exists():
        raise SystemExit("site/data.js not found — run `python run.py` first.")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://127.0.0.1:{PORT}/index.html"
        print(f"Serving {SITE} at {url}\nCtrl-C to stop.")
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
