from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from bootstrap.bootstrap import App
from campaign.adapters.handlers.http import Handler as CampaignHandler
from httpwire import HttpRequest, Response
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
                    return Response.problem(404, "not_found", "unknown route")
                headers = {name.lower(): value for name, value in self.headers.items()}
                body = self.rfile.read(HttpRequest.buffered_length(headers))
                return found.endpoint(
                    HttpRequest(
                        method=method,
                        path=self.path,
                        path_params=found.path_params,
                        query_params=found.query_params,
                        headers=headers,
                        body=body,
                    )
                )

            return Response.respond(run)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, resp: Response) -> None:
            self.send_response(resp.status_code)
            self.send_header("Content-Length", str(len(resp.body)))
            for name, value in resp.headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(resp.body)

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
