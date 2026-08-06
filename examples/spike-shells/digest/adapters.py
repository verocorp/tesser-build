import tesser.adapters as ts

import spike.client as spike_client


class NoteGateway(ts.Gateway):

    def __init__(self, notes: spike_client.NoteClient) -> None:
        self._notes = notes

    def record(self, text: str) -> str:
        return self._notes.create(spike_client.CreateNoteRequest(text=text)).text
