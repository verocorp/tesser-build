import tesser.adapters as ts

import digest.application.ports.note_taker as note_taker
import spike.client.client as spike_client


class NoteGateway(ts.Gateway):

    def __init__(self, notes: spike_client.NoteClient) -> None:
        self._notes = notes

    def record(self, request: note_taker.RecordNoteRequest) -> note_taker.RecordNoteResponse:
        created = self._notes.create(spike_client.CreateNoteRequest(text=request.text))
        return note_taker.RecordNoteResponse(text=created.text)
