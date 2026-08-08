import tesser.testing as ts

import spike.domain.notes as notes


@ts.helper
def note_spec(text: str = "remember the milk") -> notes.NoteSpec:
    return notes.NoteSpec(text=text)


def test_note_keeps_its_text() -> None:
    assert notes.Note(note_spec()).text() == "remember the milk"


def test_note_rejects_empty_text() -> None:
    spec = note_spec(text="")
    try:
        notes.Note(spec)
    except ValueError:
        return
    raise AssertionError("empty text must be rejected")
