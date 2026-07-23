from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bootstrap.bootstrap import App
from campaign.adapters.handlers.http import Handler as CampaignHandler
from httpwire import Response, problem
from reports.adapters.handlers.http import Handler as ReportsHandler


def make_server(addr: tuple[str, int], app: App) -> ThreadingHTTPServer:
    campaign_handler = CampaignHandler(app.campaign)
    reports_handler = ReportsHandler(app.reports)

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
            self._send(_not_found())

        def do_GET(self) -> None:
            if self.path.startswith("/campaigns/"):
                self._send(campaign_handler.get_campaign(self.path.removeprefix("/campaigns/")))
                return
            if self.path.startswith("/r/"):
                self._send(campaign_handler.resolve(self.path.removeprefix("/r/")))
                return
            if self.path == "/reports/links-by-verdict":
                self._send(reports_handler.links_by_verdict())
                return
            self._send(_not_found())

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


def _not_found() -> Response:
    return Response(404, problem("not_found", "unknown route"))


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
