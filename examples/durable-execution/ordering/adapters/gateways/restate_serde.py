from __future__ import annotations

import json

import tesser.adapters as ts
import restate.serde


class RecordSerde[T](restate.serde.Serde[T]):  # tesser:debt TB052

    def __init__(self, kind: type[T]) -> None:
        self._kind = kind

    def serialize(self, obj: T | None) -> bytes:
        if obj is None:
            return b""
        return json.dumps(vars(obj)).encode()

    def deserialize(self, buf: bytes) -> T | None:
        if not buf:
            return None
        return self._kind(**json.loads(buf))
