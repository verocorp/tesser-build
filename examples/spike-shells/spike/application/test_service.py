import pytest
import tesser.testing as ts

import spike.application.ports.note_repository as note_repository
import spike.application.service as application
import spike.client.client as client


@ts.fake
class FakeNoteRepository(note_repository.NoteRepository):

    def __init__(self) -> None:
        self.saved: list[note_repository.SaveNoteRequest] = []

    def save(self, request: note_repository.SaveNoteRequest) -> note_repository.SaveNoteResponse:
        self.saved.append(request)
        return note_repository.SaveNoteResponse()


def test_create_builds_the_aggregate_and_saves_its_parts() -> None:
    repository = FakeNoteRepository()
    service = application.NoteService(repository)

    response = service.create(client.CreateNoteRequest(text="write the spike"))

    assert isinstance(response, client.CreateNoteResponse)
    assert response.text == "write the spike"
    assert len(repository.saved) == 1
    assert isinstance(repository.saved[0], note_repository.SaveNoteRequest)
    assert repository.saved[0].text == "write the spike"


def test_invalid_text_rejects_and_saves_nothing() -> None:
    repository = FakeNoteRepository()
    service = application.NoteService(repository)

    with pytest.raises(ValueError):
        service.create(client.CreateNoteRequest(text=""))

    assert repository.saved == []
