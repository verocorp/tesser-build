from __future__ import annotations

import enum
import typing

import tesser.application as ts


class NameVerdict(enum.Enum):
    ALLOWED = "allowed"
    RESERVED = "reserved"


class CheckNameRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class CheckNameResponse(ts.Response):

    def __init__(self, verdict: NameVerdict, reason: str) -> None:
        self.verdict = verdict
        self.reason = reason


class NamePolicy(ts.Port, typing.Protocol):

    def check(self, request: CheckNameRequest) -> CheckNameResponse: ...
