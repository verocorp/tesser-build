from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.client as client  # tesser:debt TB070
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


@ts.fake
class FakeUserInputTranscribedEvent(client.UserInputTranscribedEvent):

    def __init__(self, transcript: str, is_final: bool) -> None:
        self._transcript = transcript
        self._is_final = is_final

    @property
    def transcript(self) -> str:
        return self._transcript

    @property
    def is_final(self) -> bool:
        return self._is_final


class TestCallEventsService:

    async def test_a_final_event_delivers_the_domain_normalized_utterance(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        user_input_transcribed_response = await call_events_service.user_input_transcribed(
            client.UserInputTranscribedRequest(
                call_id="c7", event=FakeUserInputTranscribedEvent("  my name is Grace \n", True)
            )
        )

        assert [(request.call_id, request.text) for request in fake_call_events_relay.uttered] == [
            ("c7", "my name is Grace")
        ]
        assert user_input_transcribed_response.call_id == "c7"

    async def test_an_interim_event_is_not_delivered_to_the_relay(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.user_input_transcribed(
            client.UserInputTranscribedRequest(call_id="c7", event=FakeUserInputTranscribedEvent("my na", False))
        )

        assert fake_call_events_relay.uttered == []

    async def test_a_blank_final_event_is_not_delivered_to_the_relay(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.user_input_transcribed(
            client.UserInputTranscribedRequest(call_id="c7", event=FakeUserInputTranscribedEvent(" \t\n", True))
        )

        assert fake_call_events_relay.uttered == []
