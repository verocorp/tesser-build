import typing

import tesser.context as ts


class CheckRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class CheckResponse(ts.Response):

    def __init__(self, findings: tuple[str, ...]) -> None:
        self.findings = findings


class CheckFileRequest(ts.Request):

    def __init__(self, tree: str, path: str) -> None:
        self.tree = tree
        self.path = path


class CheckFileResponse(ts.Response):

    def __init__(
        self, governance: str, findings: tuple[str, ...], codes: tuple[str, ...]
    ) -> None:
        self.governance = governance
        self.findings = findings
        self.codes = codes


class HookRequest(ts.Request):

    def __init__(self, tree: str, path: str, conf: str) -> None:
        self.tree = tree
        self.path = path
        self.conf = conf


class HookResponse(ts.Response):

    def __init__(
        self,
        governance: str,
        mode: str,
        action: str,
        findings: tuple[str, ...],
        codes: tuple[str, ...],
    ) -> None:
        self.governance = governance
        self.mode = mode
        self.action = action
        self.findings = findings
        self.codes = codes


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

    def check_file(self, check_file_request: CheckFileRequest) -> CheckFileResponse: ...

    def hook(self, hook_request: HookRequest) -> HookResponse: ...

    def mark(self, mark_request: MarkRequest) -> MarkResponse: ...

    def rename(self, rename_request: RenameRequest) -> RenameResponse: ...

    def rulebook(self, rulebook_request: RulebookRequest) -> RulebookResponse: ...
