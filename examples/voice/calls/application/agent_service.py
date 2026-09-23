from __future__ import annotations

import tesser.application as ts

import calls.client as client
import calls.domain as domain


class MapToAttendCallResponse(ts.Mapper, client.AttendCallResponse):
    def __init__(self, call_id: domain.CallId) -> None:
        super().__init__(call_id=str(call_id))


class MapToSpeakUtteranceResponse(ts.Mapper, client.SpeakUtteranceResponse):
    def __init__(self, call_id: domain.CallId, utterance: domain.Utterance) -> None:
        super().__init__(call_id=str(call_id), text=str(utterance))


class AgentService(ts.ApplicationService):
    async def attend_call(
        self, attend_call_request: client.AttendCallRequest
    ) -> client.AttendCallResponse:
        call_id = domain.CallId(attend_call_request.call_id)
        return MapToAttendCallResponse(call_id)

    async def speak_utterance(
        self, speak_utterance_request: client.SpeakUtteranceRequest
    ) -> client.SpeakUtteranceResponse:
        call_id = domain.CallId(speak_utterance_request.call_id)
        utterance = domain.Utterance(speak_utterance_request.text)
        return MapToSpeakUtteranceResponse(call_id, utterance)
