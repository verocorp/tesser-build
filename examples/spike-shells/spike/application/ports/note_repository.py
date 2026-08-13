from __future__ import annotations

from typing import Protocol

import tesser.application as ts


class SaveNoteRequest(ts.Request):

    def __init__(self, text: str) -> None:
        self.text = text


class SaveNoteResponse(ts.Response):

    def __init__(self) -> None:
        return None


class NoteRepository(ts.Port, Protocol):

    def save(self, request: SaveNoteRequest) -> SaveNoteResponse: ...
