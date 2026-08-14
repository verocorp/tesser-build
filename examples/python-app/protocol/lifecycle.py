from __future__ import annotations

import threading
from typing import Protocol

import tesser.srv as ts


class Host(ts.Port, Protocol):
    def run(self, stop: threading.Event) -> None: ...
