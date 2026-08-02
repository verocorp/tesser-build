import tesser.adapters as ts

from spike.application import NoteParts


class MemoryNoteRepository(ts.Repository):

    def __init__(self) -> None:
        self.saved: list[NoteParts] = []

    def save(self, parts: NoteParts) -> None:
        self.saved.append(parts)
