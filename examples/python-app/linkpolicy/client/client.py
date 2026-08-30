from __future__ import annotations

import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, target_url: str) -> None:
        self.target_url = target_url


class CheckResponse(ts.Response):

    def __init__(self, decision: str, reason: str) -> None:
        self.decision = decision
        self.reason = reason


class ListVerdictsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class VerdictView(ts.Response):

    def __init__(self, target_url: str, decision: str, reason: str) -> None:
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class ListVerdictsResponse(ts.Response):

    def __init__(self, verdicts: tuple[VerdictView, ...]) -> None:
        self.verdicts = verdicts


class Client(ts.Client, typing.Protocol):

    def check(self, req: CheckRequest) -> CheckResponse: ...

    def list_verdicts(self, req: ListVerdictsRequest) -> ListVerdictsResponse: ...