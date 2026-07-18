"""The HTTP host (delivery mechanism 1). It is the env edge: ``main`` populates
the spec-shaped ``Config`` directly with ``os.getenv`` calls (including its own
launch config, the listen addr) and hands it to ``bootstrap.new`` ONCE, which
validates fail-fast. It mounts the contexts' inbound handlers + the in-process
reports read, and serves. It is the only exiter.

A real service would resolve secret *references* (Vault/AWS/GCP) here too; that
launch-time loader is a legitimate host-side concern, deliberately not built.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bootstrap.bootstrap import App, new
from bootstrap.config import Config
from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from campaign.adapters.handlers.http import Handler, Response


def make_server(addr: tuple[str, int], app: App) -> ThreadingHTTPServer:
    """Mount the app's handlers on an HTTP server. Built from a single ``App`` —
    the graph is not reconstructed per request."""
    campaign_handler = Handler(app.campaign)
    reports = app.reports

    class _RequestHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/links":
                self._send(Response(404, {"type": "/problems/not_found", "detail": "unknown route"}))
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            self._send(campaign_handler.create_link(raw))  # Moment 1 fires here (vet -> create)

        def do_GET(self) -> None:
            if self.path != "/reports/links-by-verdict":
                self._send(Response(404, {"type": "/problems/not_found", "detail": "unknown route"}))
                return
            rows = [
                {"slug": r.slug, "target_url": r.target_url, "allowed": r.allowed, "reason": r.reason}
                for r in reports.links_by_verdict()  # Moment 2: in-process cross-context read
            ]
            self._send(Response(200, {"links": rows}))

        def log_message(self, format: str, *args: Any) -> None:  # quiet in the example
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
    # The host is the env edge: a missing coordinate stays empty and
    # bootstrap.new fails fast on it — it never defaults to volatile storage.
    cfg = Config(
        campaign=CampaignConfig(storage=os.getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=LinkPolicyConfig(storage=os.getenv("LINKPOLICY_STORAGE") or ""),
    )
    app = new(cfg)  # graph built once per process
    host = os.getenv("HTTP_HOST") or ""  # the host's OWN launch config, same edge
    port = int(os.getenv("HTTP_PORT") or "8080")
    server = make_server((host, port), app)
    print(f"campaign+linkpolicy app listening on {host or '0.0.0.0'}:{port}")  # noqa: T201
    try:
        server.serve_forever()
    finally:
        app.close()


if __name__ == "__main__":
    main()
