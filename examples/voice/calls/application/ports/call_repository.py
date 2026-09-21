from __future__ import annotations

import enum
import typing

import tesser.application as ts


class LoadCallOutcome(enum.Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"


class Call(ts.Response):

    def __init__(self, call_id: str, person_name: str) -> None:
        self.call_id = call_id
        self.person_name = person_name


class IssueCallIdRequest(ts.Request):

    def __init__(self) -> None:
        return None


class IssueCallIdResponse(ts.Response):

    def __init__(self, call_id: str) -> None:
        self.call_id = call_id


class SaveCallRequest(ts.Request):

    def __init__(self, call_id: str, person_name: str) -> None:
        self.call_id = call_id
        self.person_name = person_name


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

    async def issue_call_id(self, issue_call_id_request: IssueCallIdRequest) -> IssueCallIdResponse: ...

    async def save_call(self, save_call_request: SaveCallRequest) -> SaveCallResponse: ...

    async def load_call(self, load_call_request: LoadCallRequest) -> LoadCallResponse: ...


class CallStore(ts.Store, typing.Protocol):

    def transaction(self) -> typing.AsyncContextManager[CallRepository]: ...
