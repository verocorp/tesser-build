import tesser.testing as ts

from digest.adapters import NoteGateway
from digest.application import DigestService
from digest.client import DigestRequest, DigestResponse
from spike.application import NoteParts, NoteRepository, NoteService


@ts.fake
class DroppedNotes(NoteRepository):

    def save(self, parts: NoteParts) -> None:
        return None


def test_digest_reaches_spike_only_through_its_client() -> None:
    gateway = NoteGateway(NoteService(DroppedNotes()))
    service = DigestService(gateway)

    response = service.digest(DigestRequest(text="ship the rulebook"))

    assert isinstance(response, DigestResponse)
    assert response.headline == "SHIP THE RULEBOOK"
