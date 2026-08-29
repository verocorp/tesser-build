from __future__ import annotations

import enum
import typing

import tesser.application as ts


class Verdict(enum.Enum):
    OK = "ok"
    REFUSED = "refused"


class CheckRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class CheckResponse(ts.Response):

    def __init__(self, verdict: Verdict) -> None:
        self.verdict = verdict


class BetaCheck(ts.Port, typing.Protocol):

    async def check(self, request: CheckRequest) -> CheckResponse: ...
