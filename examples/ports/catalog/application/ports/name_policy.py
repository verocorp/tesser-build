from __future__ import annotations

import enum
import typing

import tesser.application as ts


class CheckNameOutcome(enum.Enum):
    ALLOWED = "allowed"
    RESERVED = "reserved"


class CheckNameRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class CheckNameResponse(ts.Response):

    def __init__(self, outcome: CheckNameOutcome, reason: str) -> None:
        self.outcome = outcome
        self.reason = reason


class NamePolicy(ts.Port, typing.Protocol):

    def check_name(self, check_name_request: CheckNameRequest) -> CheckNameResponse: ...
