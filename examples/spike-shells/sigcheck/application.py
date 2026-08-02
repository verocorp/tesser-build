from typing import Protocol

import tesser.application as ts

from sigcheck.client import CheckRequest, CheckResponse
from sigcheck.domain import Codebase, Module


class SourceReader(ts.Port, Protocol):

    def modules(self, root: str) -> tuple[Module, ...]: ...


class SigcheckService(ts.ApplicationService):

    def __init__(self, reader: SourceReader) -> None:
        self._reader = reader

    def check(self, request: CheckRequest) -> CheckResponse:
        codebase = Codebase(self._reader.modules(request.root))
        return CheckResponse(findings=tuple(str(violation) for violation in codebase.violations()))
