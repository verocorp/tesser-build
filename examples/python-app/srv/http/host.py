from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Final

import tesser.srv as ts

from bootstrap.bootstrap import App
import campaign.adapters.handlers.http as http
from errors import DomainError, InfraError, status_for
from protocol.http import BadRequest, HttpRequest, HttpResponse, PayloadTooLarge, StreamingUnsupported
import reports.adapters.handlers.http as reports_http
from srv.http.router import Route, match

MAX_BUFFERED_BODY: Final[int] = 1_048_576


@ts.function
def buffered_length(headers: Iterable[tuple[str, str]]) -> int:
    lengths: list[str] = []
    streaming = False
    for name, value in headers:
        lowered = name.lower()
        if lowered == "transfer-encoding":
            streaming = True
        elif lowered == "content-length":
            lengths.append(value.strip())
    if streaming:
        raise StreamingUnsupported(
            "this host buffers; declare a Content-Length (streaming bodies are a documented boundary)"
        )
    if not lengths:
        return 0
    if len(set(lengths)) > 1:
        raise BadRequest(f"conflicting Content-Length headers: {', '.join(lengths)}")
    raw = lengths[0]
    if not raw.isascii() or not raw.isdigit():
        raise BadRequest(f"invalid Content-Length: {raw!r}")
    declared = int(raw)
    if declared > MAX_BUFFERED_BODY:
        raise PayloadTooLarge(f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit")
    return declared


@ts.function
def respond(run: Callable[[], HttpResponse]) -> HttpResponse:
    try:
        return run()
    except BadRequest as e:
        return HttpResponse.problem(400, "malformed_request", str(e))
    except PayloadTooLarge as e:
        return HttpResponse.problem(413, "payload_too_large", str(e))
    except StreamingUnsupported as e:
        return HttpResponse.problem(411, "length_required", str(e))
    except DomainError as e:
        return HttpResponse.problem(status_for(e.kind), e.code, e.message)
    except InfraError:
        return HttpResponse.problem(503, "unavailable", "a dependency is unavailable; please retry")
    except Exception:
        return HttpResponse.problem(500, "internal", "unexpected error")


@ts.function
def routes_for(app: App) -> tuple[Route, ...]:
    campaign = http.Handler(app.campaign)
    reports = reports_http.Handler(app.reports)
    return (
        Route("POST", "/campaigns", campaign.create_campaign),
        Route("POST", "/links", campaign.add_link),
        Route("POST", "/links/deactivate", campaign.deactivate_link),
        Route("GET", "/campaigns/{campaign_id}", campaign.get_campaign),
        Route("GET", "/r/{slug}", campaign.resolve),
        Route("GET", "/reports/links-by-verdict", reports.links_by_verdict),
    )


@ts.function
def make_server(addr: tuple[str, int], app: App) -> ThreadingHTTPServer:
    routes = routes_for(app)

    class _RequestHandler(BaseHTTPRequestHandler):
        timeout = 30

        def do_GET(self) -> None:
            self._send(self._dispatch("GET"))

        def do_POST(self) -> None:
            self._send(self._dispatch("POST"))

        def _dispatch(self, method: str) -> HttpResponse:
            def run() -> HttpResponse:
                found = match(routes, method, self.path)
                if found is None:
                    return HttpResponse.problem(404, "not_found", "unknown route")
                declared = self.headers.items()
                headers = {name.lower(): value for name, value in declared}
                body = self.rfile.read(buffered_length(declared))
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

            return respond(run)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, resp: HttpResponse) -> None:
            self.send_response(resp.status_code)
            self.send_header("Content-Length", str(len(resp.body)))
            for name, value in resp.headers.items():
                if name.lower() == "content-length":
                    continue
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(resp.body)

    return ThreadingHTTPServer(addr, _RequestHandler)


class HttpHost(ts.Host):
    def __init__(self, addr: tuple[str, int], app: App) -> None:
        self._server = make_server(addr, app)

    def run(self, stop: threading.Event) -> None:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        stop.wait()
        self._server.shutdown()
        self._server.server_close()
        thread.join()
