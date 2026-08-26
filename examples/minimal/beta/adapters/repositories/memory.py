from __future__ import annotations

import tesser.adapters as ts

import beta.application.ports.key_store as key_store


class MemoryKeyStore(ts.Repository):

    def __init__(self, key: str) -> None:
        self._key = key

    def has(self, request: key_store.HasKeyRequest) -> key_store.HasKeyResponse:
        held = key_store.Held.YES if request.key == self._key else key_store.Held.NO
        return key_store.HasKeyResponse(held=held)

    def close(self) -> None:
        return None
