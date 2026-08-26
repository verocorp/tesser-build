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


class KeyRepository(ts.Port, typing.Protocol):

    def has(self, request: HasKeyRequest) -> HasKeyResponse: ...
