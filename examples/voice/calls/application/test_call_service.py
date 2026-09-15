from __future__ import annotations

import contextlib
import typing

import pytest

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.client as client


@ts.fake
class FakeConductCallRelay(relays.ConductCallRelay):

    def __init__(self) -> None:
        self.conducted: list[relays.ConductCallRequest] = []

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        self.conducted.append(conduct_call_request)
        return relays.ConductCallResponse(call_id=conduct_call_request.call_id)


@ts.fake
class FakeCallRepository(ports.CallRepository):

    def __init__(self, calls: dict[str, ports.Call]) -> None:
        self._calls = calls

    async def issue_call_id(self, issue_call_id_request: ports.IssueCallIdRequest) -> ports.IssueCallIdResponse:
        return ports.IssueCallIdResponse(call_id="issued-1")

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        self._calls[save_call_request.call_id] = ports.Call(
            call_id=save_call_request.call_id,
            person_name=save_call_request.person_name,
            phone_number=save_call_request.phone_number,
        )
        return ports.SaveCallResponse(call_id=save_call_request.call_id)

    async def load_call(self, load_call_request: ports.LoadCallRequest) -> ports.LoadCallResponse:
        if load_call_request.call_id not in self._calls:
            return ports.LoadCallResponse(outcome=ports.LoadCallOutcome.NOT_FOUND, calls=())
        return ports.LoadCallResponse(
            outcome=ports.LoadCallOutcome.FOUND, calls=(self._calls[load_call_request.call_id],)
        )


@ts.fake
class FakeCallStore(ports.CallStore):

    def __init__(self) -> None:
        self.calls: dict[str, ports.Call] = {}

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[ports.CallRepository]:
        yield FakeCallRepository(self.calls)


@ts.helper
def place_call_request(person_name: str = "Ada", phone_number: str = "+15555550100") -> client.PlaceCallRequest:
    return client.PlaceCallRequest(person_name=person_name, phone_number=phone_number)


class TestCallService:

    async def test_placing_a_call_conducts_it_for_the_person_it_was_placed_for(self) -> None:
        fake_conduct_call_relay = FakeConductCallRelay()
        call_service = application.CallService(fake_conduct_call_relay, FakeCallStore())

        place_call_response = await call_service.place_call(place_call_request(person_name="Grace"))

        assert [
            (conducted.call_id, conducted.person_name) for conducted in fake_conduct_call_relay.conducted
        ] == [(place_call_response.call_id, "Grace")]

    async def test_a_placed_call_takes_the_call_id_the_store_issued(self) -> None:
        call_service = application.CallService(FakeConductCallRelay(), FakeCallStore())

        place_call_response = await call_service.place_call(place_call_request())

        assert place_call_response.call_id == "issued-1"

    async def test_a_saved_call_is_read_back_by_its_call_id(self) -> None:
        fake_call_store = FakeCallStore()
        fake_call_store.calls["c1"] = ports.Call(call_id="c1", person_name="Grace", phone_number="+15555550100")
        call_service = application.CallService(FakeConductCallRelay(), fake_call_store)

        get_call_response = await call_service.get_call(client.GetCallRequest(call_id="c1"))

        assert get_call_response.call.person_name == "Grace"

    async def test_a_call_that_was_never_placed_is_not_found(self) -> None:
        call_service = application.CallService(FakeConductCallRelay(), FakeCallStore())

        with pytest.raises(client.CallNotFound) as raised:
            await call_service.get_call(client.GetCallRequest(call_id="never-placed"))

        assert str(raised.value) == "no call 'never-placed'"
