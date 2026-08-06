import tesser.testing as ts

import spike.domain as domain


@ts.helper
def note_spec(text: str = "remember the milk") -> domain.NoteSpec:
    return domain.NoteSpec(text=text)


def test_note_keeps_its_text() -> None:
    assert domain.Note(note_spec()).text() == "remember the milk"


def test_note_rejects_empty_text() -> None:
    spec = note_spec(text="")
    try:
        domain.Note(spec)
    except ValueError:
        return
    raise AssertionError("empty text must be rejected")
