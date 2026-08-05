import pytest
import tesser.testing as ts

from spike.application import NoteParts, NoteRepository, NoteService
from spike.client import CreateNoteRequest, CreateNoteResponse


@ts.fake
class MemoryNoteRepository(NoteRepository):

    def __init__(self) -> None:
        self.saved: list[NoteParts] = []

    def save(self, parts: NoteParts) -> None:
        self.saved.append(parts)


def test_create_builds_the_aggregate_and_saves_its_parts() -> None:
    repository = MemoryNoteRepository()
    service = NoteService(repository)

    response = service.create(CreateNoteRequest(text="write the spike"))

    assert isinstance(response, CreateNoteResponse)
    assert response.text == "write the spike"
    assert len(repository.saved) == 1
    assert isinstance(repository.saved[0], NoteParts)
    assert repository.saved[0].text == "write the spike"


def test_invalid_text_rejects_and_saves_nothing() -> None:
    repository = MemoryNoteRepository()
    service = NoteService(repository)

    with pytest.raises(ValueError):
        service.create(CreateNoteRequest(text=""))

    assert repository.saved == []
