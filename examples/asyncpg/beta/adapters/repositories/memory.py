from __future__ import annotations

import tesser.adapters as ts

import beta.application.ports.key_repository as key_repository


class MemoryKeyRepository(ts.Repository):

    def __init__(self) -> None:
        self._keys: set[str] = set()

    async def has(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        held = key_repository.Held.YES if request.key in self._keys else key_repository.Held.NO
        return key_repository.HasKeyResponse(held=held)

    async def put(self, request: key_repository.PutKeyRequest) -> key_repository.PutKeyResponse:
        self._keys.add(request.key)
        return key_repository.PutKeyResponse(key=request.key)

    async def close(self) -> None:
        self._keys.clear()
