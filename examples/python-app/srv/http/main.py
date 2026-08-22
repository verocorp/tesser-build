from __future__ import annotations

import signal
import threading
from types import FrameType
from typing import Optional

import tesser.srv as ts

from app.loader import load
from srv.http.host import HttpHost


@ts.do_not_use_function
def main() -> None:  # tesser:debt TB051
    app = load()
    host = HttpHost((app.http.host, app.http.port), app)
    print(f"campaign+linkpolicy app listening on {app.http.host or '0.0.0.0'}:{app.http.port}")  # noqa: T201
    stop = threading.Event()

    def _handle(signum: int, frame: Optional[FrameType]) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    try:
        host.run(stop)
    finally:
        app.close()


if __name__ == "__main__":  # tesser:debt TB051
    main()
