from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays
import calls.domain as domain


class MapToPersonUtteranceRequest(ts.Mapper, relays.PersonUtteranceRequest):

    def __init__(self, person_utterance_request: relays.PersonUtteranceRequest, utterance: domain.Utterance) -> None:
        super().__init__(call_id=person_utterance_request.call_id, text=str(utterance))


class CallEventsService(ts.ApplicationService):

    def __init__(self, call_events_relay: relays.CallEventsRelay) -> None:
        self._call_events_relay = call_events_relay

    async def person_utterance(  # tesser:debt TB081
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse:
        try:
            utterance = domain.Utterance(person_utterance_request.text)
        except ValueError:
            return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)
        return await self._call_events_relay.run_person_utterance(
            MapToPersonUtteranceRequest(person_utterance_request, utterance)
        )
