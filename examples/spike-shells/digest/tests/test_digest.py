import tesser.testing as ts

import digest.adapters.gateways as adapters
import digest.application.service as application
import digest.client.client as client
import spike.application.ports.note_repository as note_repository
import spike.application.service as spike_application


@ts.fake
class FakeNoteRepositoryDropping(note_repository.NoteRepository):

    def save(self, request: note_repository.SaveNoteRequest) -> note_repository.SaveNoteResponse:
        return note_repository.SaveNoteResponse()


def test_digest_reaches_spike_only_through_its_client() -> None:
    gateway = adapters.NoteGateway(spike_application.NoteService(FakeNoteRepositoryDropping()))
    service = application.DigestService(gateway)

    response = service.digest(client.DigestRequest(text="ship the rulebook"))

    assert isinstance(response, client.DigestResponse)
    assert response.headline == "SHIP THE RULEBOOK"
