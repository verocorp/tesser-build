from __future__ import annotations

import calls.domain as domain


class TestCall:

    def test_a_call_constructs_from_its_spec(self) -> None:
        call_spec = domain.CallSpec(person_name="Ada", phone_number="+15555550100")

        call = domain.Call(call_spec)

        assert str(call.person_name) == call_spec.person_name
        assert str(call.phone_number) == call_spec.phone_number

    def test_each_call_takes_an_identity_of_its_own(self) -> None:
        call_spec = domain.CallSpec(person_name="Ada", phone_number="+15555550100")

        first = domain.Call(call_spec)
        second = domain.Call(call_spec)

        assert first.identity != second.identity


class TestCallId:

    def test_a_call_id_equals_by_value(self) -> None:
        first = domain.CallId("c1")
        second = domain.CallId("c1")

        assert first == second
        assert first != domain.CallId("c2")
