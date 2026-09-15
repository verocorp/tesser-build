from __future__ import annotations

import enum
import typing

import tesser.application as ts


class LoadCallOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class Call(ts.Response):

    def __init__(self, call_id: str, person_name: str, phone_number: str) -> None:
        self.call_id = call_id
        self.person_name = person_name
        self.phone_number = phone_number


class SaveCallRequest(ts.Request):

    def __init__(self, call_id: str, person_name: str, phone_number: str) -> None:
        self.call_id = call_id
        self.person_name = person_name
        self.phone_number = phone_number


class SaveCallResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class LoadCallRequest(ts.Request):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class LoadCallResponse(ts.Response):

    def __init__(self, outcome: LoadCallOutcome, calls: tuple[Call, ...]) -> None:
        self.outcome = outcome
        self.calls = calls


class CallRepository(ts.Port, typing.Protocol):

    async def save_call(self, save_call_request: SaveCallRequest) -> SaveCallResponse: ...

    async def load_call(self, load_call_request: LoadCallRequest) -> LoadCallResponse: ...


class CallStore(ts.Store, typing.Protocol):

    def transaction(self) -> typing.AsyncContextManager[CallRepository]: ...
