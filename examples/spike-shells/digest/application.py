from typing import Protocol

import tesser.application as ts

from digest.client import DigestRequest, DigestResponse


class NoteTaker(ts.Port, Protocol):

    def record(self, text: str) -> str: ...


class DigestService(ts.ApplicationService):

    def __init__(self, notes: NoteTaker) -> None:
        self._notes = notes

    def digest(self, request: DigestRequest) -> DigestResponse:
        recorded = self._notes.record(request.text)
        return DigestResponse(headline=recorded.upper())
