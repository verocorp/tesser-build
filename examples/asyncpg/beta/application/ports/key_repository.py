from __future__ import annotations

import enum
import typing

import tesser.application as ts


class Held(enum.Enum):
    YES = "yes"
    NO = "no"


class HasKeyRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class HasKeyResponse(ts.Response):

    def __init__(self, held: Held) -> None:
        self.held = held


class PutKeyRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class PutKeyResponse(ts.Response):

    def __init__(self, key: str) -> None:
        self.key = key


class KeyRepository(ts.Port, typing.Protocol):

    async def has_key(self, has_key_request: HasKeyRequest) -> HasKeyResponse: ...

    async def put_key(self, put_key_request: PutKeyRequest) -> PutKeyResponse: ...


class KeyStore(ts.Store, typing.Protocol):

    def transaction(self) -> typing.AsyncContextManager[KeyRepository]: ...
