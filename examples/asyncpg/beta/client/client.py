from __future__ import annotations

import typing

import tesser.context as ts


class CheckKeyRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class CheckKeyResponse(ts.Response):

    def __init__(self, held: str) -> None:
        self.held = held


class HoldKeyRequest(ts.Request):

    def __init__(self, key: str) -> None:
        self.key = key


class HoldKeyResponse(ts.Response):

    def __init__(self, key: str) -> None:
        self.key = key


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Unavailable(ts.Error):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


ERRORS: typing.Final[tuple[type[Rejected], type[Unavailable]]] = (Rejected, Unavailable)


class BetaClient(ts.Client, typing.Protocol):

    async def check_key(self, check_key_request: CheckKeyRequest) -> CheckKeyResponse: ...

    async def hold_key(self, hold_key_request: HoldKeyRequest) -> HoldKeyResponse: ...
