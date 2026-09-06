import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class CheckResponse(ts.Response):

    def __init__(self, findings: tuple[str, ...]) -> None:
        self.findings = findings


class RulebookRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class RulebookResponse(ts.Response):

    def __init__(self, rendered: str) -> None:
        self.rendered = rendered


class TessercheckClient(ts.Client, typing.Protocol):

    def check(self, check_request: CheckRequest) -> CheckResponse: ...

    def rulebook(self, rulebook_request: RulebookRequest) -> RulebookResponse: ...
