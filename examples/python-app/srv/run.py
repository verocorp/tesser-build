from __future__ import annotations

import signal
import threading
from types import FrameType
from typing import Optional

from lifecycle import Closeable, Host


def run_until_signal(host: Host, app: Closeable) -> None:
    stop = threading.Event()

    def _handle(signum: int, frame: Optional[FrameType]) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    try:
        host.run(stop)
    finally:
        app.close()
