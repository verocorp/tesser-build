from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays
import calls.client as client
import calls.domain as domain


class MapToPersonJoinedRequest(ts.Mapper, relays.PersonJoinedRequest):
    def __init__(self, call_id: domain.CallId) -> None:
        super().__init__(call_id=str(call_id))


class MapToPersonJoinedResponse(ts.Mapper, client.PersonJoinedResponse):
    def __init__(self, person_joined_response: relays.PersonJoinedResponse) -> None:
        super().__init__(call_id=person_joined_response.call_id)


class MapToPersonTurnCompletedRequest(ts.Mapper, relays.PersonTurnCompletedRequest):
    def __init__(self, call_id: domain.CallId, utterance: domain.Utterance) -> None:
        super().__init__(call_id=str(call_id), text=str(utterance))


class MapToPersonTurnCompletedResponse(ts.Mapper, client.PersonTurnCompletedResponse):
    def __init__(self, person_turn_completed_response: relays.PersonTurnCompletedResponse) -> None:
        super().__init__(call_id=person_turn_completed_response.call_id)


class CallEventsService(ts.ApplicationService):
    def __init__(self, call_orchestrator_relay: relays.CallOrchestratorRelay) -> None:
        self._call_orchestrator_relay = call_orchestrator_relay

    async def person_joined(self, person_joined_request: client.PersonJoinedRequest) -> client.PersonJoinedResponse:
        call_id = domain.CallId(person_joined_request.call_id)
        person_joined_response = await self._call_orchestrator_relay.run_person_joined(
            MapToPersonJoinedRequest(call_id)
        )
        return MapToPersonJoinedResponse(person_joined_response)

    async def person_turn_completed(
        self, person_turn_completed_request: client.PersonTurnCompletedRequest
    ) -> client.PersonTurnCompletedResponse:
        call_id = domain.CallId(person_turn_completed_request.call_id)
        utterance = domain.Utterance(person_turn_completed_request.text)
        person_turn_completed_response = await self._call_orchestrator_relay.run_person_turn_completed(
            MapToPersonTurnCompletedRequest(call_id, utterance)
        )
        return MapToPersonTurnCompletedResponse(person_turn_completed_response)
