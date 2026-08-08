from typing import Protocol

import tesser.context as ts


class CreateNoteRequest(ts.Request):

    def __init__(self, text: str) -> None:
        self.text = text


class CreateNoteResponse(ts.Response):

    def __init__(self, text: str) -> None:
        self.text = text


class NoteClient(ts.Client, Protocol):

    def create(self, request: CreateNoteRequest) -> CreateNoteResponse: ...
