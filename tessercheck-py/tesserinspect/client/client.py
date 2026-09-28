import typing

import tesser.context as ts


class InspectTestsRequest(ts.Request):
    def __init__(self, repo: str, base: str) -> None:
        self.repo = repo
        self.base = base


class InspectTestsResponse(ts.Response):
    def __init__(
        self,
        baseline: str,
        changes: tuple[tuple[str, str, str], ...],
        changed_tests: tuple[str, ...],
        candidates: tuple[tuple[str, str, int, str, str], ...],
        working_tree_changes: tuple[tuple[str, str, str, str], ...],
    ) -> None:
        self.baseline = baseline
        self.changes = changes
        self.changed_tests = changed_tests
        self.candidates = candidates
        self.working_tree_changes = working_tree_changes


class InspectionFailed(ts.Error):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


ERRORS: typing.Final[tuple[type[InspectionFailed]]] = (InspectionFailed,)


class InspectionClient(ts.Client, typing.Protocol):
    def inspect_tests(
        self, inspect_tests_request: InspectTestsRequest
    ) -> InspectTestsResponse: ...
