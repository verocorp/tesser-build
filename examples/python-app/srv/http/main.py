from __future__ import annotations

import signal
import threading
import types
import typing

import tesser.srv as ts

import app.loader as loader
import srv.http.host as host


class HttpEdge(ts.Host):

    def __init__(self) -> None:
        self._app = loader.load()
        self._host = host.HttpHost((self._app.http.host, self._app.http.port), self._app)
        self._stop = threading.Event()

    def stop(self, signum: int, frame: typing.Optional[types.FrameType]) -> None:
        self._stop.set()

    def run(self, argv: list[str]) -> int:
        app = self._app
        print(f"campaign+linkpolicy app listening on {app.http.host or '0.0.0.0'}:{app.http.port}")  # noqa: T201
        signal.signal(signal.SIGINT, self.stop)  # tesser:debt TB051
        signal.signal(signal.SIGTERM, self.stop)  # tesser:debt TB051
        try:
            self._host.run(self._stop)
        finally:
            app.close()
        return 0


if __name__ == "__main__":
    ts.main(HttpEdge().run)
