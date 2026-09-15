from __future__ import annotations

import typing

import tesser.application as ts


class DialPersonRequest(ts.Request):

    def __init__(self, call_id: str, phone_number: str) -> None:
        self.call_id = call_id
        self.phone_number = phone_number


class DialPersonResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class HangUpRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class HangUpResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class Dialing(ts.Port, typing.Protocol):

    async def dial_person(self, dial_person_request: DialPersonRequest) -> DialPersonResponse: ...

    async def hang_up(self, hang_up_request: HangUpRequest) -> HangUpResponse: ...
