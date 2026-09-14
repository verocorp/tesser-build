import typing

import tesser.context as ts


class CheckTreeRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class CheckTreeResponse(ts.Response):

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


class CheckWriteRequest(ts.Request):

    def __init__(self, tree: str, path: str, conf: str) -> None:
        self.tree = tree
        self.path = path
        self.conf = conf


class CheckWriteResponse(ts.Response):

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


class MarkDebtRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class MarkDebtResponse(ts.Response):

    def __init__(self, files: int, remaining: tuple[str, ...]) -> None:
        self.files = files
        self.remaining = remaining


class RenderRulebookRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class RenderRulebookResponse(ts.Response):

    def __init__(self, rendered: str) -> None:
        self.rendered = rendered


class ApplyRenamesRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class ApplyRenamesResponse(ts.Response):

    def __init__(self, files: int, remaining: tuple[str, ...]) -> None:
        self.files = files
        self.remaining = remaining


class RulebookNotRendered(ts.Error):

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[RulebookNotRendered]]] = (RulebookNotRendered,)


class TessercheckClient(ts.Client, typing.Protocol):

    def check_tree(self, check_tree_request: CheckTreeRequest) -> CheckTreeResponse: ...

    def check_file(self, check_file_request: CheckFileRequest) -> CheckFileResponse: ...

    def check_write(self, check_write_request: CheckWriteRequest) -> CheckWriteResponse: ...

    def mark_debt(self, mark_debt_request: MarkDebtRequest) -> MarkDebtResponse: ...

    def apply_renames(self, apply_renames_request: ApplyRenamesRequest) -> ApplyRenamesResponse: ...

    def render_rulebook(self, render_rulebook_request: RenderRulebookRequest) -> RenderRulebookResponse: ...
