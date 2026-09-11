from __future__ import annotations

import http.server as server
import signal
import threading
import types
import typing

import tesser.srv as ts

import app as app
import campaign.adapters.handlers as campaign_handlers
import protocol as protocol
import reports.adapters.handlers as reports_handlers
import tesser.errors as errors

MAX_BUFFERED_BODY: typing.Final[int] = 1_048_576




class HttpHost(ts.Host):
    def __init__(self, addr: tuple[str, int], python_app: app.PythonApp) -> None:
        campaign_http_handler = campaign_handlers.HttpHandler(python_app.campaign.client)
        reports_http_handler = reports_handlers.HttpHandler(python_app.reports.client)
        routes = (
            protocol.Route("POST", "/campaigns", campaign_http_handler.create_campaign),
            protocol.Route("POST", "/links", campaign_http_handler.add_link),
            protocol.Route("POST", "/links/deactivate", campaign_http_handler.deactivate_link),
            protocol.Route("GET", "/campaigns/{campaign_id}", campaign_http_handler.get_campaign),
            protocol.Route("GET", "/r/{slug}", campaign_http_handler.resolve),
            protocol.Route("GET", "/reports/links-by-verdict", reports_http_handler.links_by_verdict),
        )
        router = protocol.Router(routes)

        class _RequestHandler(server.BaseHTTPRequestHandler):
            timeout = 30

            def do_GET(self) -> None:
                try:
                    found = router.match("GET", self.path)
                    if found is None:
                        http_response = protocol.HttpResponse.problem(404, "not_found", "unknown route")
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
                            raise protocol.StreamingUnsupported(
                                "this host buffers; declare a Content-Length "
                                "(streaming bodies are a documented boundary)"
                            )
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise protocol.BadRequest(
                                    f"conflicting Content-Length headers: {', '.join(lengths)}"
                                )
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise protocol.BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise protocol.PayloadTooLarge(
                                    f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit"
                                )
                        http_response = found.endpoint(
                            protocol.HttpRequest(
                                method="GET",
                                path=self.path,
                                path_params=found.path_params,
                                query_params=found.query_params,
                                headers=headers,
                                body=self.rfile.read(buffered),
                            )
                        )
                except protocol.BadRequest as e:
                    http_response = protocol.HttpResponse.problem(400, "malformed_request", str(e))
                except protocol.PayloadTooLarge as e:
                    http_response = protocol.HttpResponse.problem(413, "payload_too_large", str(e))
                except protocol.StreamingUnsupported as e:
                    http_response = protocol.HttpResponse.problem(411, "length_required", str(e))
                except errors.DomainError as e:
                    http_response = protocol.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
                except errors.InfraError:
                    http_response = protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                except Exception:
                    http_response = protocol.HttpResponse.problem(500, "internal", "unexpected error")
                self.send_response(http_response.status_code)
                self.send_header("Content-Length", str(len(http_response.body)))
                for name, value in http_response.headers.items():
                    if name.lower() == "content-length":
                        continue
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(http_response.body)

            def do_POST(self) -> None:
                try:
                    found = router.match("POST", self.path)
                    if found is None:
                        http_response = protocol.HttpResponse.problem(404, "not_found", "unknown route")
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
                            raise protocol.StreamingUnsupported(
                                "this host buffers; declare a Content-Length "
                                "(streaming bodies are a documented boundary)"
                            )
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise protocol.BadRequest(
                                    f"conflicting Content-Length headers: {', '.join(lengths)}"
                                )
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise protocol.BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise protocol.PayloadTooLarge(
                                    f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit"
                                )
                        http_response = found.endpoint(
                            protocol.HttpRequest(
                                method="POST",
                                path=self.path,
                                path_params=found.path_params,
                                query_params=found.query_params,
                                headers=headers,
                                body=self.rfile.read(buffered),
                            )
                        )
                except protocol.BadRequest as e:
                    http_response = protocol.HttpResponse.problem(400, "malformed_request", str(e))
                except protocol.PayloadTooLarge as e:
                    http_response = protocol.HttpResponse.problem(413, "payload_too_large", str(e))
                except protocol.StreamingUnsupported as e:
                    http_response = protocol.HttpResponse.problem(411, "length_required", str(e))
                except errors.DomainError as e:
                    http_response = protocol.HttpResponse.problem(errors.status_for(e.kind), e.code, e.message)
                except errors.InfraError:
                    http_response = protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                except Exception:
                    http_response = protocol.HttpResponse.problem(500, "internal", "unexpected error")
                self.send_response(http_response.status_code)
                self.send_header("Content-Length", str(len(http_response.body)))
                for name, value in http_response.headers.items():
                    if name.lower() == "content-length":
                        continue
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(http_response.body)

            def log_message(self, format: str, *args: typing.Any) -> None:  # tesser:debt TB022
                return

        self._server = server.ThreadingHTTPServer(addr, _RequestHandler)
        self._stop = threading.Event()

    def stop(
        self, signum: int = 0, frame: typing.Optional[types.FrameType] = None
    ) -> None:
        self._stop.set()

    def run(self, argv: list[str]) -> None:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        self._stop.wait()
        self._server.shutdown()
        self._server.server_close()
        thread.join()


class HttpEdge(ts.Host):

    def __init__(self) -> None:
        self._app = app.load()
        self._http_host = HttpHost((self._app.http.host, self._app.http.port), self._app)

    def run(self, argv: list[str]) -> int:
        python_app = self._app
        print(f"campaign+linkpolicy app listening on {python_app.http.host or '0.0.0.0'}:{python_app.http.port}")  # noqa: T201
        signal.signal(signal.SIGINT, self._http_host.stop)
        signal.signal(signal.SIGTERM, self._http_host.stop)
        try:
            self._http_host.run(argv)
        finally:
            python_app.close()
        return 0


if __name__ == "__main__":
    ts.main(HttpEdge().run)
