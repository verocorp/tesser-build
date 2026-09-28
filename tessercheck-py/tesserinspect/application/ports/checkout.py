import typing

import tesser.application as ts


class ReadCheckoutRequest(ts.Request):
    def __init__(self, repo: str, base: str) -> None:
        self.repo = repo
        self.base = base


class ReadCheckoutResponse(ts.Response):
    def __init__(
        self,
        baseline: str,
        sources: tuple[tuple[str, str], ...],
        changes: tuple[tuple[str, str, str], ...],
        paths: tuple[str, ...],
        working_tree_changes: tuple[tuple[str, str, str, str], ...],
    ) -> None:
        self.baseline = baseline
        self.sources = sources
        self.changes = changes
        self.paths = paths
        self.working_tree_changes = working_tree_changes


class CheckoutReader(ts.Port, typing.Protocol):
    def read_checkout(
        self, read_checkout_request: ReadCheckoutRequest
    ) -> ReadCheckoutResponse: ...
