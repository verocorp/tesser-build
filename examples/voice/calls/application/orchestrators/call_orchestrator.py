from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays
import calls.domain as domain

_SILENCE_SECONDS: typing.Final[int] = 8


class MapToDialPersonRequest(ts.Mapper, relays.DialPersonRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAwaitPersonAnsweredRequest(ts.Mapper, relays.AwaitPersonAnsweredRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity))


class MapToSpeakTurnRequest(ts.Mapper, relays.SpeakTurnRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAwaitPersonUtteranceRequest(ts.Mapper, relays.AwaitPersonUtteranceRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity), within_seconds=_SILENCE_SECONDS)


class MapToHangUpRequest(ts.Mapper, relays.HangUpRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToRecordCallRequest(ts.Mapper, relays.RecordCallRequest):

    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAgentTurnSpec(ts.Mapper, domain.AgentTurnSpec):

    def __init__(self, speak_turn_response: relays.SpeakTurnResponse) -> None:
        super().__init__(text=speak_turn_response.text, person_names=speak_turn_response.person_names)


class MapToConductCallResponse(ts.Mapper, relays.ConductCallResponse):

    def __init__(self, record_call_response: relays.RecordCallResponse) -> None:
        super().__init__(call_id=record_call_response.call_id)


class CallOrchestrator(ts.Orchestrator):

    def __init__(
        self,
        dial_person_relay: relays.DialPersonRelay,
        await_person_answered_relay: relays.AwaitPersonAnsweredRelay,
        speak_turn_relay: relays.SpeakTurnRelay,
        await_person_utterance_relay: relays.AwaitPersonUtteranceRelay,
        hang_up_relay: relays.HangUpRelay,
        record_call_relay: relays.RecordCallRelay,
    ) -> None:
        self._dial_person_relay = dial_person_relay
        self._await_person_answered_relay = await_person_answered_relay
        self._speak_turn_relay = speak_turn_relay
        self._await_person_utterance_relay = await_person_utterance_relay
        self._hang_up_relay = hang_up_relay
        self._record_call_relay = record_call_relay

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        call = conduct_call_request.call
        await self._dial_person_relay.run_dial_person(MapToDialPersonRequest(call))
        await self._await_person_answered_relay.await_person_answered(MapToAwaitPersonAnsweredRequest(call))
        while True:
            match conduct_call_request.call.progress():  # tesser:debt TB082
                case domain.CallProgress.ENDED:
                    break
                case domain.CallProgress.AGENTS_TURN:
                    speak_turn_response = await self._speak_turn_relay.run_speak_turn(MapToSpeakTurnRequest(call))
                    call.agent_said(domain.AgentTurn(MapToAgentTurnSpec(speak_turn_response)))
                case domain.CallProgress.PERSONS_TURN:
                    await_person_utterance_response = (
                        await self._await_person_utterance_relay.await_person_utterance(
                            MapToAwaitPersonUtteranceRequest(call)
                        )
                    )
                    call.person_said(await_person_utterance_response.text)
                case _ as never:
                    typing.assert_never(never)
        await self._hang_up_relay.run_hang_up(MapToHangUpRequest(call))
        record_call_response = await self._record_call_relay.run_record_call(MapToRecordCallRequest(call))
        return MapToConductCallResponse(record_call_response)
