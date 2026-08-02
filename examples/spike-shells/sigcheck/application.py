from typing import Protocol

import tesser.application as ts

from sigcheck.client import CheckRequest, CheckResponse
from sigcheck.domain import Codebase, CodebaseSpec


class SourceReader(ts.Port, Protocol):

    def sources(self, root: str) -> tuple[tuple[str, str], ...]: ...


class SigcheckService(ts.ApplicationService):

    def __init__(self, reader: SourceReader) -> None:
        self._reader = reader

    def check(self, request: CheckRequest) -> CheckResponse:
        codebase = Codebase(CodebaseSpec(sources=self._reader.sources(request.root)))
        return CheckResponse(findings=tuple(str(violation) for violation in codebase.violations()))
