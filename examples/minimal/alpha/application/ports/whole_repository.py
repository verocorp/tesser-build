from __future__ import annotations

import enum
import typing

import tesser.application as ts


class Lookup(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class WholeRecord(ts.Response):

    def __init__(self, id: str, name: str, count: int) -> None:
        self.id = id
        self.name = name
        self.count = count


class SaveWholeRequest(ts.Request):

    def __init__(self, id: str, name: str, count: int) -> None:
        self.id = id
        self.name = name
        self.count = count


class SaveWholeResponse(ts.Response):

    def __init__(self) -> None:
        return None


class FindWholeRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class FindWholeResponse(ts.Response):

    def __init__(self, outcome: Lookup, wholes: tuple[WholeRecord, ...]) -> None:
        self.outcome = outcome
        self.wholes = wholes


class WholeRepository(ts.Port, typing.Protocol):

    def save(self, request: SaveWholeRequest) -> SaveWholeResponse: ...

    def find(self, request: FindWholeRequest) -> FindWholeResponse: ...
