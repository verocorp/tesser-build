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

    async def has_key(self, request: HasKeyRequest) -> HasKeyResponse: ...

    async def put_key(self, request: PutKeyRequest) -> PutKeyResponse: ...


class KeyStore(ts.Port, typing.Protocol):  # tesser:debt TB052

    def transaction(self) -> typing.AsyncContextManager[KeyRepository]: ...  # tesser:debt TB081
