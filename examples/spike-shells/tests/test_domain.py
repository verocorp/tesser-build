import tesser.testing as ts

from spike.domain import Note, NoteSpec


@ts.helper
def note_spec(text: str = "remember the milk") -> NoteSpec:
    return NoteSpec(text=text)


def test_note_keeps_its_text() -> None:
    assert Note(note_spec()).text() == "remember the milk"


def test_note_rejects_empty_text() -> None:
    spec = note_spec(text="")
    try:
        Note(spec)
    except ValueError:
        return
    raise AssertionError("empty text must be rejected")
