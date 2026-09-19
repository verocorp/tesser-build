from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.client as client  # tesser:debt TB060
import calls.application.relays as relays
import calls.domain as domain


class MapToUserInputTranscribedSpec(ts.Mapper, domain.UserInputTranscribedSpec):

    def __init__(self, user_input_transcribed_request: client.UserInputTranscribedRequest) -> None:
        super().__init__(
            call_id=user_input_transcribed_request.call_id,
            transcript=user_input_transcribed_request.event.transcript,
            is_final=user_input_transcribed_request.event.is_final,
        )


class MapToPersonUtteranceRequest(ts.Mapper, relays.PersonUtteranceRequest):

    def __init__(self, user_input_transcribed: domain.UserInputTranscribed) -> None:
        super().__init__(
            call_id=str(user_input_transcribed.call_id), text=str(user_input_transcribed.utterances[0])
        )


class CallEventsService(ts.ApplicationService):

    def __init__(self, call_events_relay: relays.CallEventsRelay) -> None:
        self._call_events_relay = call_events_relay

    async def user_input_transcribed(  # tesser:debt TB081
        self, user_input_transcribed_request: client.UserInputTranscribedRequest
    ) -> client.UserInputTranscribedResponse:
        user_input_transcribed = domain.UserInputTranscribed(MapToUserInputTranscribedSpec(user_input_transcribed_request))
        match user_input_transcribed.decide():
            case domain.TranscriptionDecision.DELIVER:
                await self._call_events_relay.run_person_utterance(MapToPersonUtteranceRequest(user_input_transcribed))
            case domain.TranscriptionDecision.IGNORE:
                pass
            case _ as never:
                typing.assert_never(never)
        return client.UserInputTranscribedResponse(call_id=user_input_transcribed_request.call_id)
