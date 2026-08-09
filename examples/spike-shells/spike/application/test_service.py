import pytest
import tesser.testing as ts

import spike.application.service as application
import spike.client.client as client


@ts.fake
class MemoryNoteRepository(application.NoteRepository):

    def __init__(self) -> None:
        self.saved: list[application.NoteParts] = []

    def save(self, parts: application.NoteParts) -> None:
        self.saved.append(parts)


def test_create_builds_the_aggregate_and_saves_its_parts() -> None:
    repository = MemoryNoteRepository()
    service = application.NoteService(repository)

    response = service.create(client.CreateNoteRequest(text="write the spike"))

    assert isinstance(response, client.CreateNoteResponse)
    assert response.text == "write the spike"
    assert len(repository.saved) == 1
    assert isinstance(repository.saved[0], application.NoteParts)
    assert repository.saved[0].text == "write the spike"


def test_invalid_text_rejects_and_saves_nothing() -> None:
    repository = MemoryNoteRepository()
    service = application.NoteService(repository)

    with pytest.raises(ValueError):
        service.create(client.CreateNoteRequest(text=""))

    assert repository.saved == []
