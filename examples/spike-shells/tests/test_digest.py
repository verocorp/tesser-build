import tesser.testing as ts

import digest.adapters.gateways as adapters
import digest.application.service as application
import digest.client.client as client
import spike.application.service as spike_application


@ts.fake
class DroppedNotes(spike_application.NoteRepository):

    def save(self, parts: spike_application.NoteParts) -> None:
        return None


def test_digest_reaches_spike_only_through_its_client() -> None:
    gateway = adapters.NoteGateway(spike_application.NoteService(DroppedNotes()))
    service = application.DigestService(gateway)

    response = service.digest(client.DigestRequest(text="ship the rulebook"))

    assert isinstance(response, client.DigestResponse)
    assert response.headline == "SHIP THE RULEBOOK"
