from __future__ import annotations

import tesser.application as ts

import digest.application.ports.note_taker as note_taker
import digest.client.client as client


class DigestService(ts.ApplicationService):

    def __init__(self, notes: note_taker.NoteTaker) -> None:
        self._notes = notes

    def digest(self, request: client.DigestRequest) -> client.DigestResponse:
        recorded = self._notes.record(note_taker.RecordNoteRequest(text=request.text))
        return client.DigestResponse(headline=recorded.text.upper())
