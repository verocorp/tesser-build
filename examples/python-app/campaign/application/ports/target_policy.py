from __future__ import annotations

import enum
import typing

import tesser.application as ts


class PolicyVerdict(enum.Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


class CheckTargetRequest(ts.Request):

    def __init__(self, target_url: str) -> None:
        self.target_url = target_url


class CheckTargetResponse(ts.Response):

    def __init__(self, verdict: PolicyVerdict, reason: str) -> None:
        self.verdict = verdict
        self.reason = reason


class TargetPolicy(ts.Port, typing.Protocol):

    def check(self, request: CheckTargetRequest) -> CheckTargetResponse: ...
