from typing import Protocol

import tesser.application as ts

import spike.client.client as client
import spike.domain.notes as notes


class NoteParts(ts.Parts):

    def __init__(self, text: str) -> None:
        self.text = text


class NoteRepository(ts.Port, Protocol):

    def save(self, parts: NoteParts) -> None: ...


class NoteService(ts.ApplicationService):

    def __init__(self, repository: NoteRepository) -> None:
        self._repository = repository

    def create(self, request: client.CreateNoteRequest) -> client.CreateNoteResponse:
        note = notes.Note(notes.NoteSpec(text=request.text))
        self._repository.save(NoteParts(text=note.text()))
        return client.CreateNoteResponse(text=request.text)
