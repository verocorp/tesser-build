from __future__ import annotations

import typing

import tesser.application as ts

import calls.application.relays as relays
import calls.domain as domain

_RESPONSE_START_SECONDS: typing.Final[int] = 8


class MapToDialPersonRequest(ts.Mapper, relays.DialPersonRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAwaitPersonAnsweredRequest(ts.Mapper, relays.AwaitPersonAnsweredRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity))


class MapToSpeakTurnRequest(ts.Mapper, relays.SpeakTurnRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAwaitPersonInputRequest(ts.Mapper, relays.AwaitPersonInputRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity), within_seconds=_RESPONSE_START_SECONDS)


class MapToAwaitCompletedTurnRequest(ts.Mapper, relays.AwaitPersonInputRequest):  # tesser:debt TB080
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity), within_seconds=None)


class MapToInterpretedTurnSpec(ts.Mapper, domain.InterpretedTurnSpec):
    def __init__(self, interpret_turn_response: relays.InterpretTurnResponse) -> None:
        super().__init__(person_names=interpret_turn_response.person_names)


class MapToInterpretTurnRequest(ts.Mapper, relays.InterpretTurnRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToPersonInputSpec(ts.Mapper, domain.PersonInputSpec):
    def __init__(self, await_person_input_response: relays.AwaitPersonInputResponse) -> None:
        super().__init__(kind=await_person_input_response.kind, text=await_person_input_response.text)


class MapToHangUpRequest(ts.Mapper, relays.HangUpRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToRecordCallRequest(ts.Mapper, relays.RecordCallRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAgentTurnSpec(ts.Mapper, domain.AgentTurnSpec):
    def __init__(self, speak_turn_response: relays.SpeakTurnResponse) -> None:
        super().__init__(text=speak_turn_response.text)


class MapToConductCallResponse(ts.Mapper, relays.ConductCallResponse):
    def __init__(self, record_call_response: relays.RecordCallResponse) -> None:
        super().__init__(call_id=record_call_response.call_id)


class CallOrchestrator(ts.Orchestrator):
    def __init__(
        self,
        dialing_relay: relays.DialingRelay,
        speech_relay: relays.SpeechRelay,
        person_relay: relays.PersonRelay,
        record_call_relay: relays.RecordCallRelay,
        interpretation_relay: relays.InterpretationRelay,
    ) -> None:
        self._dialing_relay = dialing_relay
        self._speech_relay = speech_relay
        self._person_relay = person_relay
        self._record_call_relay = record_call_relay
        self._interpretation_relay = interpretation_relay

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        call = conduct_call_request.call
        await self._dialing_relay.run_dial_person(MapToDialPersonRequest(call))
        await self._person_relay.await_person_answered(MapToAwaitPersonAnsweredRequest(call))
        while True:
            match conduct_call_request.call.progress():  # tesser:debt TB082
                case domain.CallProgress.ENDED:
                    break
                case domain.CallProgress.AGENTS_TURN:
                    speak_turn_response = await self._speech_relay.run_speak_turn(MapToSpeakTurnRequest(call))
                    call.agent_said(domain.AgentTurn(MapToAgentTurnSpec(speak_turn_response)))
                case domain.CallProgress.AWAITING_RESPONSE:
                    await_person_input_response = await self._person_relay.await_person_input(
                        MapToAwaitPersonInputRequest(call)
                    )
                    call.receive(domain.PersonInput(MapToPersonInputSpec(await_person_input_response)))
                case domain.CallProgress.PERSON_SPEAKING:
                    await_person_input_response = await self._person_relay.await_person_input(
                        MapToAwaitCompletedTurnRequest(call)
                    )
                    call.receive(domain.PersonInput(MapToPersonInputSpec(await_person_input_response)))
                case domain.CallProgress.INTERPRETING_TURN:
                    interpret_turn_response = await self._interpretation_relay.run_interpret_turn(
                        MapToInterpretTurnRequest(call)
                    )
                    call.interpreted(domain.InterpretedTurn(MapToInterpretedTurnSpec(interpret_turn_response)))
                case domain.CallProgress.NO_RESPONSE:
                    call.response_missing()
                case _ as never:
                    typing.assert_never(never)
        await self._dialing_relay.run_hang_up(MapToHangUpRequest(call))
        record_call_response = await self._record_call_relay.run_record_call(MapToRecordCallRequest(call))
        return MapToConductCallResponse(record_call_response)
