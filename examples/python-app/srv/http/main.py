from __future__ import annotations

import signal
import threading
from types import FrameType
from typing import Optional

import tesser.srv as ts

from app.loader import load
from srv.http.host import HttpHost


class HttpEdge(ts.Host):

    def __init__(self) -> None:
        self._app = load()
        self._host = HttpHost((self._app.http.host, self._app.http.port), self._app)
        self._stop = threading.Event()

    def stop(self, signum: int, frame: Optional[FrameType]) -> None:
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
