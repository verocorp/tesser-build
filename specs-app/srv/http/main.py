from __future__ import annotations

import http.server as server
import pathlib
import signal
import threading
import types
import typing

import tesser.srv as ts

import app as app
import protocol as protocol
import specification.adapters.handlers as handlers

MAX_BUFFERED_BODY: typing.Final[int] = 1_048_576
PAGE: typing.Final[pathlib.Path] = pathlib.Path(__file__).with_name("index.html")


class HttpHost(ts.Host):

    def __init__(self, addr: tuple[str, int], specs_app: app.SpecsApp) -> None:
        http_handler = handlers.HttpHandler(specs_app.specification.client)
        routes = (
            protocol.Route("POST", "/jtbd/{jtbd_id}/stories", http_handler.add_story),
        )
        router = protocol.Router(routes)
        page = PAGE.read_bytes()

        class _RequestHandler(server.BaseHTTPRequestHandler):
            timeout = 30

            def do_GET(self) -> None:
                if self.path.split("?")[0] == "/":
                    http_response = protocol.HttpResponse.html(page)
                else:
                    http_response = protocol.HttpResponse.problem(404, "not_found", "unknown route")
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
                            raise protocol.StreamingUnsupported("this host buffers; declare a Content-Length")
                        buffered = 0
                        if lengths:
                            if len(set(lengths)) > 1:
                                raise protocol.BadRequest(f"conflicting Content-Length headers: {', '.join(lengths)}")
                            raw = lengths[0]
                            if not raw.isascii() or not raw.isdigit():
                                raise protocol.BadRequest(f"invalid Content-Length: {raw!r}")
                            buffered = int(raw)
                            if buffered > MAX_BUFFERED_BODY:
                                raise protocol.PayloadTooLarge(f"body exceeds the {MAX_BUFFERED_BODY}-byte buffer limit")
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

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = server.ThreadingHTTPServer(addr, _RequestHandler)

    @property
    def port(self) -> int:
        port: int = self._server.server_address[1]
        return port

    def run(self, stop: threading.Event) -> None:
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        stop.wait()
        self._server.shutdown()
        self._server.server_close()
        thread.join()


class HttpEdge(ts.Host):

    def __init__(self) -> None:
        self._app = app.load()
        self._host = HttpHost((self._app.http.host, self._app.http.port), self._app)
        self._stop = threading.Event()

    def stop(self, signum: int, frame: typing.Optional[types.FrameType]) -> None:
        self._stop.set()

    def run(self, argv: list[str]) -> int:
        specs_app = self._app
        print(f"specs app listening on {specs_app.http.host or '0.0.0.0'}:{self._host.port}")  # noqa: T201
        signal.signal(signal.SIGINT, self.stop)  # tesser:debt TB051
        signal.signal(signal.SIGTERM, self.stop)  # tesser:debt TB051
        try:
            self._host.run(self._stop)
        finally:
            specs_app.close()
        return 0


if __name__ == "__main__":
    ts.main(HttpEdge().run)
