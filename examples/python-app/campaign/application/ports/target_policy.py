from __future__ import annotations

import enum
import typing

import tesser.application as ts


class CheckTargetOutcome(enum.Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"


class CheckTargetRequest(ts.Request):

    def __init__(self, target_url: str) -> None:
        self.target_url = target_url


class CheckTargetResponse(ts.Response):

    def __init__(self, outcome: CheckTargetOutcome, reason: str) -> None:
        self.outcome = outcome
        self.reason = reason


class TargetPolicy(ts.Port, typing.Protocol):

    def check_target(self, check_target_request: CheckTargetRequest) -> CheckTargetResponse: ...
