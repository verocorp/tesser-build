from typing import Protocol


class Closeable(Protocol):
    def close(self) -> None: ...
