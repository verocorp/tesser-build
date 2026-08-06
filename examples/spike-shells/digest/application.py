from typing import Protocol

import tesser.application as ts

import digest.client as client


class NoteTaker(ts.Port, Protocol):

    def record(self, text: str) -> str: ...


class DigestService(ts.ApplicationService):

    def __init__(self, notes: NoteTaker) -> None:
        self._notes = notes

    def digest(self, request: client.DigestRequest) -> client.DigestResponse:
        recorded = self._notes.record(request.text)
        return client.DigestResponse(headline=recorded.upper())
