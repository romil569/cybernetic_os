from __future__ import annotations

import json
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class SpatialWebServer:
    def __init__(self, root: Path, port: int = 8765) -> None:
        self.root, self.port = root, port
        self.state = {"command": "idle", "sequence": 0}
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> bool:
        if self._server:
            return True
        server_ref = self
        directory = str(self.root)
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/api/state":
                    payload = json.dumps(server_ref.state).encode("utf-8")
                    self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
                    return
                if parsed.path == "/api/command":
                    command = parse_qs(parsed.query).get("value", ["idle"])[0]
                    server_ref.state = {"command": command, "sequence": server_ref.state["sequence"] + 1}
                    self.send_response(204); self.end_headers(); return
                super().do_GET()
            def log_message(self, format, *args):
                return
        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
            threading.Thread(target=self._server.serve_forever, daemon=True).start()
            return True
        except OSError:
            return False

    def open(self) -> str | None:
        if not self.start():
            return None
        url = f"http://127.0.0.1:{self.port}/three_d.html"
        webbrowser.open(url)
        return url

    def command(self, value: str) -> None:
        self.state = {"command": value, "sequence": self.state["sequence"] + 1}

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        self._server = None
