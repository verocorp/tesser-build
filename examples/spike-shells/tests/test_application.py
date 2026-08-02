import pytest

from spike.client import CreateNoteRequest, CreateNoteResponse
from spike.domain import Note
from spike.adapters import MemoryNoteRepository
from spike.application import NoteService


def test_create_builds_the_aggregate_and_saves_it() -> None:
    repository = MemoryNoteRepository()
    service = NoteService(repository)

    response = service.create(CreateNoteRequest(text="write the spike"))

    assert isinstance(response, CreateNoteResponse)
    assert response.text == "write the spike"
    assert len(repository.saved) == 1
    assert isinstance(repository.saved[0], Note)


def test_invalid_text_rejects_and_saves_nothing() -> None:
    repository = MemoryNoteRepository()
    service = NoteService(repository)

    with pytest.raises(ValueError):
        service.create(CreateNoteRequest(text=""))

    assert repository.saved == []
