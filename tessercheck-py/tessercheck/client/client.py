import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class CheckResponse(ts.Response):

    def __init__(self, findings: tuple[str, ...]) -> None:
        self.findings = findings


class MarkRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class MarkResponse(ts.Response):

    def __init__(self, files: int, remaining: tuple[str, ...]) -> None:
        self.files = files
        self.remaining = remaining


class RulebookRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class RulebookResponse(ts.Response):

    def __init__(self, rendered: str) -> None:
        self.rendered = rendered


class RenameRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class RenameResponse(ts.Response):

    def __init__(self, files: int, remaining: tuple[str, ...]) -> None:
        self.files = files
        self.remaining = remaining


class Rejected(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[Rejected]]] = (Rejected,)


class TessercheckClient(ts.Client, typing.Protocol):

    def check(self, check_request: CheckRequest) -> CheckResponse: ...

    def mark(self, mark_request: MarkRequest) -> MarkResponse: ...

    def rename(self, rename_request: RenameRequest) -> RenameResponse: ...

    def rulebook(self, rulebook_request: RulebookRequest) -> RulebookResponse: ...
