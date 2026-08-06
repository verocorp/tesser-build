from typing import Protocol

import tesser.application as ts

import sigcheck.client as client
import sigcheck.domain as domain


class SourceReader(ts.Port, Protocol):

    def sources(self, root: str) -> tuple[tuple[str, str, bool], ...]: ...


class SigcheckService(ts.ApplicationService):

    def __init__(self, reader: SourceReader) -> None:
        self._reader = reader

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        codebase = domain.Codebase(domain.CodebaseSpec(sources=self._reader.sources(request.root)))
        return client.CheckResponse(findings=tuple(str(violation) for violation in codebase.violations()))
