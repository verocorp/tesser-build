import tesser.adapters as ts

from spike.client import CreateNoteRequest, NoteClient


class NoteGateway(ts.Gateway):

    def __init__(self, notes: NoteClient) -> None:
        self._notes = notes

    def record(self, text: str) -> str:
        return self._notes.create(CreateNoteRequest(text=text)).text
