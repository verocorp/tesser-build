from typing import Protocol

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, root: str) -> None:
        self.root = root


class CheckResponse(ts.Response):

    def __init__(self, findings: tuple[str, ...]) -> None:
        self.findings = findings


class Client(ts.Client, Protocol):

    def check(self, request: CheckRequest) -> CheckResponse: ...
