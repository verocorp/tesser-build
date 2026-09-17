from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.relays as relays
import calls.client as client


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

    async def test_reporting_that_the_person_answered_signals_the_call_by_its_id(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.report_person_answered(client.ReportPersonAnsweredRequest(call_id="c7"))

        assert [answered.call_id for answered in fake_call_events_relay.answered] == ["c7"]

    async def test_reporting_what_the_person_said_signals_the_call_with_their_words(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.report_person_utterance(
            client.ReportPersonUtteranceRequest(call_id="c7", text="my name is Grace")
        )

        assert [(uttered.call_id, uttered.text) for uttered in fake_call_events_relay.uttered] == [
            ("c7", "my name is Grace")
        ]

    async def test_a_report_answers_the_call_id_it_was_about(self) -> None:
        call_events_service = application.CallEventsService(FakeCallEventsRelay())

        report_person_answered_response = await call_events_service.report_person_answered(
            client.ReportPersonAnsweredRequest(call_id="c7")
        )

        assert report_person_answered_response.call_id == "c7"
