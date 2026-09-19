from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.client as client  # tesser:debt TB070
import calls.application.relays as relays


@ts.fake
class FakeCallEventsRelay(relays.CallEventsRelay):
    def __init__(self) -> None:
        self.answered: list[relays.PersonAnsweredRequest] = []
        self.uttered: list[relays.PersonInputRequest] = []

    async def run_person_answered(
        self, person_answered_request: relays.PersonAnsweredRequest
    ) -> relays.PersonAnsweredResponse:
        self.answered.append(person_answered_request)
        return relays.PersonAnsweredResponse(call_id=person_answered_request.call_id)

    async def run_person_input(self, person_input_request: relays.PersonInputRequest) -> relays.PersonInputResponse:
        self.uttered.append(person_input_request)
        return relays.PersonInputResponse(call_id=person_input_request.call_id)


@ts.fake
class FakeUserTurnMessage(client.UserTurnMessage):
    def __init__(self, text_content: str | None) -> None:
        self._text_content = text_content

    @property
    def text_content(self) -> str | None:
        return self._text_content


class TestCallEventsService:
    async def test_a_completed_turn_delivers_the_domain_normalized_utterance(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        user_turn_completed_response = await call_events_service.user_turn_completed(
            client.UserTurnCompletedRequest(call_id="c7", message=FakeUserTurnMessage("  my name is Grace \n"))
        )

        assert [(request.call_id, request.text) for request in fake_call_events_relay.uttered] == [
            ("c7", "my name is Grace")
        ]
        assert user_turn_completed_response.call_id == "c7"

    async def test_a_turn_without_text_still_delivers_the_completion_boundary(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.user_turn_completed(
            client.UserTurnCompletedRequest(call_id="c7", message=FakeUserTurnMessage(None))
        )

        assert [(r.kind, r.text) for r in fake_call_events_relay.uttered] == [(relays.INPUT_TURN_COMPLETED, "")]

    async def test_a_blank_turn_still_delivers_the_completion_boundary(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.user_turn_completed(
            client.UserTurnCompletedRequest(call_id="c7", message=FakeUserTurnMessage(" \t\n"))
        )

        assert [(r.kind, r.text) for r in fake_call_events_relay.uttered] == [(relays.INPUT_TURN_COMPLETED, "")]


@ts.fake
class FakeUserStateChangedEvent(client.UserStateChangedEvent):
    def __init__(self, new_state: str) -> None:
        self._new_state = new_state

    @property
    def new_state(self) -> str:
        return self._new_state


class TestUserStateDelivery:
    async def test_speech_start_is_delivered_without_waiting_for_words(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.user_state_changed(
            client.UserStateChangedRequest(call_id="c7", event=FakeUserStateChangedEvent("speaking"))
        )

        assert [(r.call_id, r.kind, r.text) for r in fake_call_events_relay.uttered] == [
            ("c7", relays.INPUT_SPEECH_STARTED, "")
        ]

    async def test_stopping_speech_does_not_finish_a_turn(self) -> None:
        fake_call_events_relay = FakeCallEventsRelay()
        call_events_service = application.CallEventsService(fake_call_events_relay)

        await call_events_service.user_state_changed(
            client.UserStateChangedRequest(call_id="c7", event=FakeUserStateChangedEvent("listening"))
        )

        assert fake_call_events_relay.uttered == []
