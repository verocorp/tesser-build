from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.client as client  # tesser:debt TB060
import calls.application.relays as relays
import calls.domain as domain


class MapToUserTurnCompletedSpec(ts.Mapper, domain.UserTurnCompletedSpec):
    def __init__(self, user_turn_completed_request: client.UserTurnCompletedRequest) -> None:
        super().__init__(
            call_id=user_turn_completed_request.call_id,
            text=user_turn_completed_request.message.text_content,
        )


class MapToPersonInputRequest(ts.Mapper, relays.PersonInputRequest):
    def __init__(self, user_turn_completed: domain.UserTurnCompleted) -> None:
        super().__init__(
            call_id=str(user_turn_completed.call_id),
            kind=relays.INPUT_TURN_COMPLETED,
            text=" ".join(str(u) for u in user_turn_completed.utterances),
        )


class MapToUserStateChangedSpec(ts.Mapper, domain.UserStateChangedSpec):
    def __init__(self, user_state_changed_request: client.UserStateChangedRequest) -> None:
        super().__init__(
            call_id=user_state_changed_request.call_id, new_state=user_state_changed_request.event.new_state
        )


class MapToSpeechStartedRequest(ts.Mapper, relays.PersonInputRequest):  # tesser:debt TB080
    def __init__(self, user_state_changed: domain.UserStateChanged) -> None:
        super().__init__(call_id=str(user_state_changed.call_id), kind=relays.INPUT_SPEECH_STARTED, text="")


class CallEventsService(ts.ApplicationService):
    def __init__(self, call_events_relay: relays.CallEventsRelay) -> None:
        self._call_events_relay = call_events_relay

    async def user_turn_completed(  # tesser:debt TB081
        self, user_turn_completed_request: client.UserTurnCompletedRequest
    ) -> client.UserTurnCompletedResponse:
        user_turn_completed = domain.UserTurnCompleted(MapToUserTurnCompletedSpec(user_turn_completed_request))
        await self._call_events_relay.run_person_input(MapToPersonInputRequest(user_turn_completed))
        return client.UserTurnCompletedResponse(call_id=user_turn_completed_request.call_id)

    async def user_state_changed(  # tesser:debt TB081
        self, user_state_changed_request: client.UserStateChangedRequest
    ) -> client.UserStateChangedResponse:
        user_state_changed = domain.UserStateChanged(MapToUserStateChangedSpec(user_state_changed_request))
        match user_state_changed.decide():
            case domain.InputDeliveryDecision.DELIVER:
                await self._call_events_relay.run_person_input(MapToSpeechStartedRequest(user_state_changed))
            case domain.InputDeliveryDecision.IGNORE:
                pass
            case _ as never:
                typing.assert_never(never)
        return client.UserStateChangedResponse(call_id=user_state_changed_request.call_id)
