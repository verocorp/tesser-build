from __future__ import annotations

import threading
from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...


class Host(Protocol):
    def run(self, stop: threading.Event) -> None: ...
