from __future__ import annotations

import tesser.application as ts

import spike.application.mapping as mapping
import spike.application.ports.note_repository as note_repository
import spike.client.client as client
import spike.domain.notes as notes


class NoteService(ts.ApplicationService):

    def __init__(self, repository: note_repository.NoteRepository) -> None:
        self._repository = repository

    def create(self, request: client.CreateNoteRequest) -> client.CreateNoteResponse:
        note = notes.Note(notes.NoteSpec(text=request.text))
        self._repository.save(mapping.save_request(note))
        return client.CreateNoteResponse(text=request.text)
