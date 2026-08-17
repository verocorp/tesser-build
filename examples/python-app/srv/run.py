from __future__ import annotations

import signal
import threading
from collections.abc import Callable
from types import FrameType
from typing import Optional

import tesser.srv as ts

from protocol.lifecycle import Host


@ts.do_not_use_function
def run_until_signal(host: Host, close: Callable[[], None]) -> None:
    stop = threading.Event()

    def _handle(signum: int, frame: Optional[FrameType]) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    try:
        host.run(stop)
    finally:
        close()
