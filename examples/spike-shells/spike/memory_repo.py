import tesser.adapters as ts

from spike.domain import Note


class MemoryNoteRepository(ts.Repository):

    def __init__(self) -> None:
        self.saved: list[Note] = []

    def save(self, note: Note) -> None:
        self.saved.append(note)
