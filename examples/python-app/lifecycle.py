from __future__ import annotations

from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...
