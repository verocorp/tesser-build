from typing import Protocol

import tesser.application as ts

from spike.client import CreateNoteRequest, CreateNoteResponse
from spike.domain import Note, NoteSpec


class NoteParts(ts.Parts):

    def __init__(self, text: str) -> None:
        self.text = text


def note_parts(note: Note) -> NoteParts:
    return NoteParts(text=note.text())


class NoteRepository(ts.Port, Protocol):

    def save(self, parts: NoteParts) -> None: ...


class NoteService(ts.ApplicationService):

    def __init__(self, repository: NoteRepository) -> None:
        self._repository = repository

    def create(self, request: CreateNoteRequest) -> CreateNoteResponse:
        note = Note(NoteSpec(text=request.text))
        self._repository.save(note_parts(note))
        return CreateNoteResponse(text=request.text)
