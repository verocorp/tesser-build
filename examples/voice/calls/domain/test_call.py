from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.domain as domain


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestCall:
    def test_a_new_call_asks_for_the_persons_first_name(self) -> None:
        call = domain.Call(call_spec())

        assert str(call.question) == "Hello. Please tell me your first name."
        assert str(call.person_name) == ""

    def test_the_name_is_what_the_person_said_without_surrounding_punctuation(self) -> None:
        call = domain.Call(call_spec())

        call.person_said(domain.Utterance("  Sarah. "))

        assert str(call.person_name) == "Sarah"
        assert str(call.greeting) == "Nice to meet you, Sarah. Goodbye."

    def test_a_call_is_identified_by_its_id(self) -> None:
        assert domain.Call(call_spec(call_id="c1")) == domain.Call(call_spec(call_id="c1", person_name="Ada"))
        assert domain.Call(call_spec(call_id="c1")) != domain.Call(call_spec(call_id="c2"))
        assert domain.Call(call_spec(call_id="c1")).identity == domain.CallId("c1")


class TestUtterance:
    def test_an_utterance_says_something(self) -> None:
        with pytest.raises(ValueError):
            domain.Utterance("   ")

    def test_an_utterance_is_its_trimmed_text(self) -> None:
        assert domain.Utterance(" hello ") == domain.Utterance("hello")
        assert str(domain.Utterance(" hello ")) == "hello"


class TestPersonName:
    def test_a_name_has_no_punctuation_around_it(self) -> None:
        assert domain.PersonName("Sarah.") == domain.PersonName("Sarah")
        assert str(domain.PersonName(" 'Sarah', ")) == "Sarah"


class TestCallPresence:
    def test_presence_decides_the_lookup(self) -> None:
        assert domain.CallPresence(domain.CallPresenceSpec(presence="found")).decide() is domain.CallLookup.FOUND
        assert (
            domain.CallPresence(domain.CallPresenceSpec(presence="not_found")).decide() is domain.CallLookup.NOT_FOUND
        )
