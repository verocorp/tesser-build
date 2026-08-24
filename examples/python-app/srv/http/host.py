from __future__ import annotations

import threading
import http.server as server
import typing

import tesser.srv as ts

import app.app as app_app
import campaign.adapters.handlers.http as http
import tesser.errors as errors
import protocol.http as protocol_http
import reports.adapters.handlers.http as reports_http

MAX_BUFFERED_BODY: typing.Final[int] = 1_048_576


class HttpHost(ts.Host):
    def __init__(self, addr: tuple[str, int], app: app_app.App) -> None:
        campaign = http.Handler(app.campaign.client)
        reports = reports_http.Handler(app.reports.client)
        routes = (
            protocol_http.Route("POST", "/campaigns", campaign.create_campaign),
            protocol_http.Route("POST", "/links", campaign.add_link),
            protocol_http.Route("POST", "/links/deactivate", campaign.deactivate_link),
            protocol_http.Route("GET", "/campaigns/{campaign_id}", campaign.get_campaign),
            protocol_http.Route("GET", "/r/{slug}", campaign.resolve),
            protocol_http.Route("GET", "/reports/links-by-verdict", reports.links_by_verdict),
        )
        router = protocol_http.Router(routes)

        class _RequestHandler(server.BaseHTTPRequestHandler):
            timeout = 30

            def do_GET(self) -> None:
                try:
                    found = router.match("GET", self.path)
                    if found is None:
                        resp = protocol_http.HttpResponse.problem(404, "not_found", "unknown route")
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
                            raise protocol_http.StreamingUnsupported(
                                "this host buffers; declare a Content-Length "
                                "(streaming bodies are a documented boundary)"
                            )
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise protocol_http.BadRequest(
                                    f"conflicting Content-Length headers: {', '.join(lengths)}"
                                )
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise protocol_http.BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise protocol_http.PayloadTooLarge(
                                    f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit"
                                )
                        resp = found.endpoint(
                            protocol_http.HttpRequest(
                                method="GET",
                                path=self.path,
                                path_params=found.path_params,
                                query_params=found.query_params,
                                headers=headers,
                                body=self.rfile.read(buffered),
                            )
                        )
                except protocol_http.BadRequest as e:
                    resp = protocol_http.HttpResponse.problem(400, "malformed_request", str(e))
                except protocol_http.PayloadTooLarge as e:
                    resp = protocol_http.HttpResponse.problem(413, "payload_too_large", str(e))
                except protocol_http.StreamingUnsupported as e:
                    resp = protocol_http.HttpResponse.problem(411, "length_required", str(e))
                except errors.DomainError as e:
                    resp = protocol_http.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
                except errors.InfraError:
                    resp = protocol_http.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                except Exception:
                    resp = protocol_http.HttpResponse.problem(500, "internal", "unexpected error")
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
                    found = router.match("POST", self.path)
                    if found is None:
                        resp = protocol_http.HttpResponse.problem(404, "not_found", "unknown route")
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
                            raise protocol_http.StreamingUnsupported(
                                "this host buffers; declare a Content-Length "
                                "(streaming bodies are a documented boundary)"
                            )
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise protocol_http.BadRequest(
                                    f"conflicting Content-Length headers: {', '.join(lengths)}"
                                )
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise protocol_http.BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise protocol_http.PayloadTooLarge(
                                    f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit"
                                )
                        resp = found.endpoint(
                            protocol_http.HttpRequest(
                                method="POST",
                                path=self.path,
                                path_params=found.path_params,
                                query_params=found.query_params,
                                headers=headers,
                                body=self.rfile.read(buffered),
                            )
                        )
                except protocol_http.BadRequest as e:
                    resp = protocol_http.HttpResponse.problem(400, "malformed_request", str(e))
                except protocol_http.PayloadTooLarge as e:
                    resp = protocol_http.HttpResponse.problem(413, "payload_too_large", str(e))
                except protocol_http.StreamingUnsupported as e:
                    resp = protocol_http.HttpResponse.problem(411, "length_required", str(e))
                except errors.DomainError as e:
                    resp = protocol_http.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
                except errors.InfraError:
                    resp = protocol_http.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                except Exception:
                    resp = protocol_http.HttpResponse.problem(500, "internal", "unexpected error")
                self.send_response(resp.status_code)
                self.send_header("Content-Length", str(len(resp.body)))
                for name, value in resp.headers.items():
                    if name.lower() == "content-length":
                        continue
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(resp.body)

            def log_message(self, format: str, *args: typing.Any) -> None:
                return

        self._server = server.ThreadingHTTPServer(addr, _RequestHandler)

    def run(self, stop: threading.Event) -> None:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        stop.wait()
        self._server.shutdown()
        self._server.server_close()
        thread.join()
