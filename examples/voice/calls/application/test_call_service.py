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
class FakeCallOrchestratorRelay(relays.CallOrchestratorRelay):

    def __init__(self) -> None:
        self.conducted: list[relays.ConductCallRequest] = []
        self.joined: list[relays.PersonJoinedRequest] = []
        self.completed: list[relays.PersonTurnCompletedRequest] = []

    async def run_conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        self.conducted.append(conduct_call_request)
        return relays.ConductCallResponse(call_id=str(conduct_call_request.call.identity))

    async def run_person_joined(
        self, person_joined_request: relays.PersonJoinedRequest
    ) -> relays.PersonJoinedResponse:
        self.joined.append(person_joined_request)
        return relays.PersonJoinedResponse(call_id=person_joined_request.call_id)

    async def run_person_turn_completed(
        self, person_turn_completed_request: relays.PersonTurnCompletedRequest
    ) -> relays.PersonTurnCompletedResponse:
        self.completed.append(person_turn_completed_request)
        return relays.PersonTurnCompletedResponse(call_id=person_turn_completed_request.call_id)


@ts.fake
class FakeCallRepository(ports.CallRepository):

    def __init__(self, calls: dict[str, ports.Call]) -> None:
        self._calls = calls

    async def issue_call_id(self, issue_call_id_request: ports.IssueCallIdRequest) -> ports.IssueCallIdResponse:
        return ports.IssueCallIdResponse(call_id="issued-1")

    async def save_call(self, save_call_request: ports.SaveCallRequest) -> ports.SaveCallResponse:
        self._calls[save_call_request.call_id] = ports.Call(
            call_id=save_call_request.call_id, person_name=save_call_request.person_name
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


class TestCallService:

    async def test_placing_a_call_conducts_the_call_it_answers_with(self) -> None:
        fake_call_orchestrator_relay = FakeCallOrchestratorRelay()
        call_service = application.CallService(fake_call_orchestrator_relay, FakeCallStore())

        place_call_response = await call_service.place_call(client.PlaceCallRequest())

        assert [str(conducted.call.identity) for conducted in fake_call_orchestrator_relay.conducted] == [
            place_call_response.call_id
        ]

    async def test_a_placed_call_carries_no_name_until_the_person_says_one(self) -> None:
        fake_call_orchestrator_relay = FakeCallOrchestratorRelay()
        call_service = application.CallService(fake_call_orchestrator_relay, FakeCallStore())

        await call_service.place_call(client.PlaceCallRequest())

        assert [str(conducted.call.person_name) for conducted in fake_call_orchestrator_relay.conducted] == [""]

    async def test_a_placed_call_takes_the_call_id_the_store_issued(self) -> None:
        call_service = application.CallService(FakeCallOrchestratorRelay(), FakeCallStore())

        place_call_response = await call_service.place_call(client.PlaceCallRequest())

        assert place_call_response.call_id == "issued-1"

    async def test_a_saved_call_is_read_back_by_its_call_id(self) -> None:
        fake_call_store = FakeCallStore()
        fake_call_store.calls["c1"] = ports.Call(call_id="c1", person_name="Grace")
        call_service = application.CallService(FakeCallOrchestratorRelay(), fake_call_store)

        get_call_response = await call_service.get_call(client.GetCallRequest(call_id="c1"))

        assert get_call_response.call.person_name == "Grace"

    async def test_a_call_that_was_never_placed_is_not_found(self) -> None:
        call_service = application.CallService(FakeCallOrchestratorRelay(), FakeCallStore())

        with pytest.raises(client.CallNotFound) as raised:
            await call_service.get_call(client.GetCallRequest(call_id="never-placed"))

        assert str(raised.value) == "no call 'never-placed'"
