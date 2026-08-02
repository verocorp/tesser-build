import tesser.domain as ts


class Note(ts.AggregateRoot):

    def __init__(self, text: str) -> None:
        if not text:
            raise ValueError("text must be non-empty")
        self._text = text
