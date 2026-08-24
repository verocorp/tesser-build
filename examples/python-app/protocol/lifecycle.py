from __future__ import annotations

import threading
import typing

import tesser.srv as ts


class Host(ts.Port, typing.Protocol):
    def run(self, stop: threading.Event) -> None: ...
