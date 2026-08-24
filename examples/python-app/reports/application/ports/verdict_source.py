from __future__ import annotations

import enum
import typing

import tesser.application as ts


class VerdictDecision(enum.Enum):
    ALLOWED = "allowed"
    DENIED = "denied"


class VerdictRecord(ts.Response):

    def __init__(self, target_url: str, decision: VerdictDecision, reason: str) -> None:
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class ListVerdictsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListVerdictsResponse(ts.Response):

    def __init__(self, verdicts: tuple[VerdictRecord, ...]) -> None:
        self.verdicts = verdicts


class VerdictSource(ts.Port, typing.Protocol):

    def verdicts(self, request: ListVerdictsRequest) -> ListVerdictsResponse: ...
