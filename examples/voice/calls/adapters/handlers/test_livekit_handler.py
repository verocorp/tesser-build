from __future__ import annotations

import tesser.testing as ts

import calls.adapters.handlers as handlers
import calls.client as client
import protocol


@ts.fake
class FakeCallsClient(client.CallsClient):

    def __init__(self) -> None:
        self.answered: list[client.ReportPersonAnsweredRequest] = []
        self.uttered: list[client.ReportPersonUtteranceRequest] = []

    async def place_call(self, place_call_request: client.PlaceCallRequest) -> client.PlaceCallResponse:
        return client.PlaceCallResponse(call_id="c1")

    async def get_call(self, get_call_request: client.GetCallRequest) -> client.GetCallResponse:
        return client.GetCallResponse(call=client.Call(call_id=get_call_request.call_id, person_name="Ada"))

    async def report_person_answered(
        self, report_person_answered_request: client.ReportPersonAnsweredRequest
    ) -> client.ReportPersonAnsweredResponse:
        self.answered.append(report_person_answered_request)
        return client.ReportPersonAnsweredResponse(call_id=report_person_answered_request.call_id)

    async def report_person_utterance(
        self, report_person_utterance_request: client.ReportPersonUtteranceRequest
    ) -> client.ReportPersonUtteranceResponse:
        self.uttered.append(report_person_utterance_request)
        return client.ReportPersonUtteranceResponse(call_id=report_person_utterance_request.call_id)


class TestLivekitHandler:

    async def test_a_person_answering_is_reported_to_the_context_by_the_call_id(self) -> None:
        fake_calls_client = FakeCallsClient()
        livekit_handler = handlers.LivekitHandler(fake_calls_client)

        await livekit_handler.person_answered(protocol.PersonAnswered(call_id="c7"))

        assert [answered.call_id for answered in fake_calls_client.answered] == ["c7"]

    async def test_what_a_person_said_is_reported_to_the_context_with_their_words(self) -> None:
        fake_calls_client = FakeCallsClient()
        livekit_handler = handlers.LivekitHandler(fake_calls_client)

        await livekit_handler.person_utterance(protocol.PersonUtterance(call_id="c7", text="my name is Grace"))

        assert [(uttered.call_id, uttered.text) for uttered in fake_calls_client.uttered] == [("c7", "my name is Grace")]
