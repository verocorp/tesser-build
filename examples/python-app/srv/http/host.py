from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bootstrap.bootstrap import App
from campaign.adapters.handlers.http import Handler as CampaignHandler
from httpwire import HttpRequest, Response, decode_body, problem, respond
from reports.adapters.handlers.http import Handler as ReportsHandler
from srv.http.router import Route, match


def routes_for(app: App) -> tuple[Route, ...]:
    campaign = CampaignHandler(app.campaign)
    reports = ReportsHandler(app.reports)
    return (
        Route("POST", "/campaigns", campaign.create_campaign),
        Route("POST", "/links", campaign.add_link),
        Route("POST", "/links/deactivate", campaign.deactivate_link),
        Route("GET", "/campaigns/{campaign_id}", campaign.get_campaign),
        Route("GET", "/r/{slug}", campaign.resolve),
        Route("GET", "/reports/links-by-verdict", reports.links_by_verdict),
    )


def make_server(addr: tuple[str, int], app: App) -> ThreadingHTTPServer:
    routes = routes_for(app)

    class _RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._send(self._dispatch("GET"))

        def do_POST(self) -> None:
            self._send(self._dispatch("POST"))

        def _dispatch(self, method: str) -> Response:
            def run() -> Response:
                found = match(routes, method, self.path)
                if found is None:
                    return Response(404, problem("not_found", "unknown route"))
                return found.endpoint(
                    HttpRequest(
                        method=method,
                        path=self.path,
                        path_params=found.path_params,
                        query_params=found.query_params,
                        headers={name: value for name, value in self.headers.items()},
                        body=decode_body(self._read_body()),
                    )
                )

            return respond(run)

        def _read_body(self) -> str:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0:
                return ""
            return self.rfile.read(length).decode("utf-8")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, resp: Response) -> None:
            payload = json.dumps(resp.body).encode("utf-8")
            self.send_response(resp.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for name, value in resp.headers.items():
                self.send_header(name, value)
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
