from __future__ import annotations

import pytest

import calls.domain as domain


class TestPersona:

    def test_a_persona_equals_by_value(self) -> None:
        first = domain.Persona("a friendly receptionist")
        second = domain.Persona("a friendly receptionist")

        assert first == second
        assert first != domain.Persona("a terse dispatcher")

    def test_a_persona_reads_back_as_the_words_it_was_given(self) -> None:
        persona = domain.Persona("  a friendly receptionist ")

        assert str(persona) == "a friendly receptionist"

    def test_a_blank_persona_is_refused(self) -> None:
        with pytest.raises(ValueError):
            domain.Persona("   ")
