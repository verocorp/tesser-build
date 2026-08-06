from __future__ import annotations

import threading
from typing import Protocol

import tesser.application as ts


class Closeable(ts.Port, Protocol):
    def close(self) -> None: ...


class Host(ts.Port, Protocol):
    def run(self, stop: threading.Event) -> None: ...
