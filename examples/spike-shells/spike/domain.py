import tesser.domain as ts


class NoteSpec(ts.Spec):

    def __init__(self, text: str) -> None:
        self.text = text


class Note(ts.AggregateRoot):

    def __init__(self, spec: NoteSpec) -> None:
        if not spec.text:
            raise ValueError("text must be non-empty")
        self._text = spec.text

    def text(self) -> str:
        return self._text
