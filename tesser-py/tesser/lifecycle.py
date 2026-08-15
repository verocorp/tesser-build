from typing import Protocol

from tesser.application.port import Port


class Closeable(Port, Protocol):
    def close(self) -> None: ...
