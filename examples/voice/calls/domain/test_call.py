from __future__ import annotations

import pytest

import calls.domain as domain
import tesser.errors as errors


class TestCall:

    def test_a_call_constructs_from_its_spec(self) -> None:
        call_spec = domain.CallSpec(call_id="c1", person_name="Ada", phone_number="+15555550100")

        call = domain.Call(call_spec)

        assert str(call.identity) == call_spec.call_id
        assert str(call.person_name) == call_spec.person_name
        assert str(call.phone_number) == call_spec.phone_number


class TestCallPresence:

    def test_a_call_the_store_found_decides_that_it_was_found(self) -> None:
        call_presence = domain.CallPresence(domain.CallPresenceSpec(presence="found"))

        assert call_presence.decide() is domain.CallLookup.FOUND

    def test_a_call_the_store_did_not_find_decides_that_it_was_not_found(self) -> None:
        call_presence = domain.CallPresence(domain.CallPresenceSpec(presence="not_found"))

        assert call_presence.decide() is domain.CallLookup.NOT_FOUND

    def test_a_presence_the_domain_does_not_know_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as raised:
            domain.CallPresence(domain.CallPresenceSpec(presence="maybe"))

        assert raised.value.code == "invalid_presence"


class TestCallId:

    def test_a_call_id_equals_by_value(self) -> None:
        first = domain.CallId("c1")
        second = domain.CallId("c1")

        assert first == second
        assert first != domain.CallId("c2")
