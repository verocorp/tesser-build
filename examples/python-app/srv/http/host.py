from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Final

import tesser.srv as ts

from app.app import App
import campaign.adapters.handlers.http as http
from tesser.errors import DomainError, InfraError, status_for
from protocol.http import BadRequest, HttpRequest, HttpResponse, PayloadTooLarge, StreamingUnsupported
import reports.adapters.handlers.http as reports_http
from srv.http.router import Route, match

MAX_BUFFERED_BODY: Final[int] = 1_048_576


class HttpHost(ts.Host):
    def __init__(self, addr: tuple[str, int], app: App) -> None:
        campaign = http.Handler(app.campaign.client)
        reports = reports_http.Handler(app.reports.client)
        routes = (
            Route("POST", "/campaigns", campaign.create_campaign),
            Route("POST", "/links", campaign.add_link),
            Route("POST", "/links/deactivate", campaign.deactivate_link),
            Route("GET", "/campaigns/{campaign_id}", campaign.get_campaign),
            Route("GET", "/r/{slug}", campaign.resolve),
            Route("GET", "/reports/links-by-verdict", reports.links_by_verdict),
        )

        class _RequestHandler(BaseHTTPRequestHandler):
            timeout = 30

            def do_GET(self) -> None:
                try:
                    found = match(routes, "GET", self.path)
                    if found is None:
                        resp = HttpResponse.problem(404, "not_found", "unknown route")
                    else:
                        declared = self.headers.items()
                        headers = {name.lower(): value for name, value in declared}
                        lengths: list[str] = []
                        streaming = False
                        for name, value in declared:
                            lowered = name.lower()
                            if lowered == "transfer-encoding":
                                streaming = True
                            elif lowered == "content-length":
                                lengths.append(value.strip())
                        if streaming:
                            raise StreamingUnsupported(
                                "this host buffers; declare a Content-Length "
                                "(streaming bodies are a documented boundary)"
                            )
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise BadRequest(
                                    f"conflicting Content-Length headers: {', '.join(lengths)}"
                                )
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise PayloadTooLarge(
                                    f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit"
                                )
                        resp = found.endpoint(
                            HttpRequest(
                                method="GET",
                                path=self.path,
                                path_params=found.path_params,
                                query_params=found.query_params,
                                headers=headers,
                                body=self.rfile.read(buffered),
                            )
                        )
                except BadRequest as e:
                    resp = HttpResponse.problem(400, "malformed_request", str(e))
                except PayloadTooLarge as e:
                    resp = HttpResponse.problem(413, "payload_too_large", str(e))
                except StreamingUnsupported as e:
                    resp = HttpResponse.problem(411, "length_required", str(e))
                except DomainError as e:
                    resp = HttpResponse.problem(status_for(e.kind), e.code, e.message)
                except InfraError:
                    resp = HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                except Exception:
                    resp = HttpResponse.problem(500, "internal", "unexpected error")
                self.send_response(resp.status_code)
                self.send_header("Content-Length", str(len(resp.body)))
                for name, value in resp.headers.items():
                    if name.lower() == "content-length":
                        continue
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(resp.body)

            def do_POST(self) -> None:
                try:
                    found = match(routes, "POST", self.path)
                    if found is None:
                        resp = HttpResponse.problem(404, "not_found", "unknown route")
                    else:
                        declared = self.headers.items()
                        headers = {name.lower(): value for name, value in declared}
                        lengths: list[str] = []
                        streaming = False
                        for name, value in declared:
                            lowered = name.lower()
                            if lowered == "transfer-encoding":
                                streaming = True
                            elif lowered == "content-length":
                                lengths.append(value.strip())
                        if streaming:
                            raise StreamingUnsupported(
                                "this host buffers; declare a Content-Length "
                                "(streaming bodies are a documented boundary)"
                            )
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise BadRequest(
                                    f"conflicting Content-Length headers: {', '.join(lengths)}"
                                )
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise PayloadTooLarge(
                                    f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit"
                                )
                        resp = found.endpoint(
                            HttpRequest(
                                method="POST",
                                path=self.path,
                                path_params=found.path_params,
                                query_params=found.query_params,
                                headers=headers,
                                body=self.rfile.read(buffered),
                            )
                        )
                except BadRequest as e:
                    resp = HttpResponse.problem(400, "malformed_request", str(e))
                except PayloadTooLarge as e:
                    resp = HttpResponse.problem(413, "payload_too_large", str(e))
                except StreamingUnsupported as e:
                    resp = HttpResponse.problem(411, "length_required", str(e))
                except DomainError as e:
                    resp = HttpResponse.problem(status_for(e.kind), e.code, e.message)
                except InfraError:
                    resp = HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                except Exception:
                    resp = HttpResponse.problem(500, "internal", "unexpected error")
                self.send_response(resp.status_code)
                self.send_header("Content-Length", str(len(resp.body)))
                for name, value in resp.headers.items():
                    if name.lower() == "content-length":
                        continue
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(resp.body)

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._server = ThreadingHTTPServer(addr, _RequestHandler)

    def run(self, stop: threading.Event) -> None:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        stop.wait()
        self._server.shutdown()
        self._server.server_close()
        thread.join()
