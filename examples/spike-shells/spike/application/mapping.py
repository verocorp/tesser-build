from __future__ import annotations

import tesser.application as ts

import spike.application.ports.note_repository as note_repository
import spike.domain.notes as notes


@ts.function
def save_request(entity: notes.Note) -> note_repository.SaveNoteRequest:
    return note_repository.SaveNoteRequest(text=entity.text())
