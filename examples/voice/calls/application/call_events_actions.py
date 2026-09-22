from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays
import calls.domain as domain


class MapToPersonJoinedRequest(ts.Mapper, relays.PersonJoinedRequest):
    def __init__(self, call_id: domain.CallId) -> None:
        super().__init__(call_id=str(call_id))


class MapToPersonTurnCompletedRequest(ts.Mapper, relays.PersonTurnCompletedRequest):
    def __init__(self, call_id: domain.CallId, utterance: domain.Utterance) -> None:
        super().__init__(call_id=str(call_id), text=str(utterance))


class CallEventsActions(ts.Actions):
    def __init__(self, call_events_relay: relays.CallEventsRelay) -> None:  # tesser:debt TB081
        self._call_events_relay = call_events_relay

    async def person_joined(  # tesser:debt TB082
        self, person_joined_request: relays.PersonJoinedRequest
    ) -> relays.PersonJoinedResponse:
        call_id = domain.CallId(person_joined_request.call_id)
        return await self._call_events_relay.run_person_joined(MapToPersonJoinedRequest(call_id))

    async def person_turn_completed(  # tesser:debt TB082
        self, person_turn_completed_request: relays.PersonTurnCompletedRequest
    ) -> relays.PersonTurnCompletedResponse:
        call_id = domain.CallId(person_turn_completed_request.call_id)
        utterance = domain.Utterance(person_turn_completed_request.text)
        return await self._call_events_relay.run_person_turn_completed(
            MapToPersonTurnCompletedRequest(call_id, utterance)
        )
