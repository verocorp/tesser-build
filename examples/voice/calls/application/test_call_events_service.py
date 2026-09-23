from __future__ import annotations

import pytest

import tesser.testing as ts

import calls.application as application
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


class TestCallEventsService:
    async def test_a_person_joining_reaches_the_relay_under_the_call_id(self) -> None:
        fake_call_orchestrator_relay = FakeCallOrchestratorRelay()
        call_events_service = application.CallEventsService(fake_call_orchestrator_relay)

        person_joined_response = await call_events_service.person_joined(client.PersonJoinedRequest(call_id="c7"))

        assert [joined.call_id for joined in fake_call_orchestrator_relay.joined] == ["c7"]
        assert person_joined_response.call_id == "c7"

    async def test_a_completed_turn_reaches_the_relay_as_the_trimmed_utterance(self) -> None:
        fake_call_orchestrator_relay = FakeCallOrchestratorRelay()
        call_events_service = application.CallEventsService(fake_call_orchestrator_relay)

        person_turn_completed_response = await call_events_service.person_turn_completed(
            client.PersonTurnCompletedRequest(call_id="c7", text="  my name is Grace \n")
        )

        assert [(completed.call_id, completed.text) for completed in fake_call_orchestrator_relay.completed] == [
            ("c7", "my name is Grace")
        ]
        assert person_turn_completed_response.call_id == "c7"

    async def test_a_turn_that_says_nothing_is_refused(self) -> None:
        call_events_service = application.CallEventsService(FakeCallOrchestratorRelay())

        with pytest.raises(ValueError):
            await call_events_service.person_turn_completed(
                client.PersonTurnCompletedRequest(call_id="c7", text=" \t\n")
            )

    async def test_a_turn_that_says_nothing_never_reaches_the_relay(self) -> None:
        fake_call_orchestrator_relay = FakeCallOrchestratorRelay()
        call_events_service = application.CallEventsService(fake_call_orchestrator_relay)

        with pytest.raises(ValueError):
            await call_events_service.person_turn_completed(
                client.PersonTurnCompletedRequest(call_id="c7", text=" \t\n")
            )

        assert fake_call_orchestrator_relay.completed == []
