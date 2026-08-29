from __future__ import annotations

import asyncio
import contextlib
import typing

import tesser.adapters as ts

import beta.application.ports.key_repository as key_repository


class MemoryKeyRepository(ts.Repository):

    def __init__(self, keys: set[str]) -> None:
        self._keys = keys

    async def has_key(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        held = key_repository.Held.YES if request.key in self._keys else key_repository.Held.NO
        return key_repository.HasKeyResponse(held=held)

    async def put_key(self, request: key_repository.PutKeyRequest) -> key_repository.PutKeyResponse:
        self._keys.add(request.key)
        return key_repository.PutKeyResponse(key=request.key)


class MemoryKeyStore(ts.Repository):

    def __init__(self) -> None:
        self._keys: set[str] = set()
        self._transacting = asyncio.Lock()

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[key_repository.KeyRepository]:
        async with self._transacting:
            keys_before = set(self._keys)
            try:
                yield MemoryKeyRepository(self._keys)
            except BaseException:
                self._keys.clear()
                self._keys.update(keys_before)
                raise
