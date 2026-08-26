from __future__ import annotations


class MemoryClient:

    def __init__(self) -> None:
        self._keys = frozenset({"k"})

    def exists(self, key: str) -> bool:
        return key in self._keys
