from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bootstrap.bootstrap import App
from campaign.adapters.handlers.http import Handler, Response


def make_server(addr: tuple[str, int], app: App) -> ThreadingHTTPServer:
    campaign_handler = Handler(app.campaign)
    reports = app.reports

    class _RequestHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            if self.path == "/campaigns":
                self._send(campaign_handler.create_campaign(raw))
                return
            if self.path == "/links":
                self._send(campaign_handler.add_link(raw))
                return
            self._send(Response(404, {"type": "/problems/not_found", "detail": "unknown route"}))

        def do_GET(self) -> None:
            if self.path.startswith("/campaigns/"):
                self._send(campaign_handler.get_campaign(self.path.removeprefix("/campaigns/")))
                return
            if self.path.startswith("/r/"):
                self._send(campaign_handler.resolve(self.path.removeprefix("/r/")))
                return
            if self.path != "/reports/links-by-verdict":
                self._send(Response(404, {"type": "/problems/not_found", "detail": "unknown route"}))
                return
            rows = [
                {"slug": r.slug, "target_url": r.target_url, "allowed": r.allowed, "reason": r.reason}
                for r in reports.links_by_verdict()
            ]
            self._send(Response(200, {"links": rows}))

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, resp: Response) -> None:
            payload = json.dumps(resp.body).encode("utf-8")
            self.send_response(resp.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return ThreadingHTTPServer(addr, _RequestHandler)


class HttpHost:
    def __init__(self, addr: tuple[str, int], app: App) -> None:
        self._server = make_server(addr, app)

    def run(self, stop: threading.Event) -> None:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        stop.wait()
        self._server.shutdown()
        self._server.server_close()
        thread.join()
