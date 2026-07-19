from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bootstrap.bootstrap import App, new
from bootstrap.config import Config
from campaign.adapters.handlers.http import Handler, Response
from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig


def make_server(addr: tuple[str, int], app: App) -> ThreadingHTTPServer:
    campaign_handler = Handler(app.campaign)
    reports = app.reports

    class _RequestHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/links":
                self._send(Response(404, {"type": "/problems/not_found", "detail": "unknown route"}))
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            self._send(campaign_handler.create_link(raw))

        def do_GET(self) -> None:
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


def main() -> None:
    cfg = Config(
        campaign=CampaignConfig(storage=os.getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=LinkPolicyConfig(storage=os.getenv("LINKPOLICY_STORAGE") or ""),
        reports=ReportsConfig(),
    )
    app = new(cfg)
    host = os.getenv("HTTP_HOST") or ""
    port = int(os.getenv("HTTP_PORT") or "8080")
    server = make_server((host, port), app)
    print(f"campaign+linkpolicy app listening on {host or '0.0.0.0'}:{port}")  # noqa: T201
    try:
        server.serve_forever()
    finally:
        app.close()


if __name__ == "__main__":
    main()
