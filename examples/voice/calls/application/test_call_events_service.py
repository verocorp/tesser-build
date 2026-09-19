from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.relays as relays


@ts.fake
class FakeCallEventsRelay(relays.CallEventsRelay):

    def __init__(self) -> None:
        self.answered: list[relays.PersonAnsweredRequest] = []
        self.uttered: list[relays.PersonUtteranceRequest] = []

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        self.answered.append(person_answered_request)
        return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

    async def run_person_utterance(
        self, person_utterance_request: relays.PersonUtteranceRequest
    ) -> relays.PersonUtteranceResponse:
        self.uttered.append(person_utterance_request)
        return relays.PersonUtteranceResponse(call_id=person_utterance_request.call_id)


class TestCallEventsService:

    async def test_an_utterance_is_normalized_before_relay_delivery(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        person_utterance_response = await call_events_service.person_utterance(
            relays.PersonUtteranceRequest(call_id="c7", text="  my name is Grace \n")
        )

        assert [(request.call_id, request.text) for request in fake_call_events_relay.uttered] == [
            ("c7", "my name is Grace")
        ]
        assert person_utterance_response.call_id == "c7"

    async def test_a_blank_transcript_is_not_delivered_as_an_utterance(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.person_utterance(relays.PersonUtteranceRequest(call_id="c7", text=" \t\n"))

        assert fake_call_events_relay.uttered == []
