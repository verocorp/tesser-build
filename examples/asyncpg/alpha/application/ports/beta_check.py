from __future__ import annotations

import enum
import typing

import tesser.application as ts


class CheckNameOutcome(enum.Enum):
    OK = "ok"
    REFUSED = "refused"


class CheckNameRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class CheckNameResponse(ts.Response):

    def __init__(self, outcome: CheckNameOutcome) -> None:
        self.outcome = outcome


class BetaCheck(ts.Port, typing.Protocol):

    async def check_name(self, check_name_request: CheckNameRequest) -> CheckNameResponse: ...
