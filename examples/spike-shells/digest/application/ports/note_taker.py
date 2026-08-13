from __future__ import annotations

from typing import Protocol

import tesser.application as ts


class RecordNoteRequest(ts.Request):

    def __init__(self, text: str) -> None:
        self.text = text


class RecordNoteResponse(ts.Response):

    def __init__(self, text: str) -> None:
        self.text = text


class NoteTaker(ts.Port, Protocol):

    def record(self, request: RecordNoteRequest) -> RecordNoteResponse: ...
