from typing import Protocol

import tesser.application as ts

from spike.client import CreateNoteRequest, CreateNoteResponse
from spike.domain import Note


class NoteRepository(ts.Port, Protocol):

    def save(self, note: Note) -> None: ...


class NoteService(ts.ApplicationService):

    def __init__(self, repository: NoteRepository) -> None:
        self._repository = repository

    def create(self, request: CreateNoteRequest) -> CreateNoteResponse:
        note = Note(request.text)
        self._repository.save(note)
        return CreateNoteResponse(text=request.text)
