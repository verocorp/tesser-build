from __future__ import annotations

import tesser.application as ts

import calls.application.relays as relays
import calls.domain as domain


class MapToDialPersonRequest(ts.Mapper, relays.DialPersonRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToAwaitPersonJoinedRequest(ts.Mapper, relays.AwaitPersonJoinedRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity))


class MapToSayUtteranceRequest(ts.Mapper, relays.SayUtteranceRequest):
    def __init__(self, call: domain.Call, utterance: domain.Utterance) -> None:
        super().__init__(call_id=str(call.identity), text=str(utterance))


class MapToAwaitPersonTurnCompletedRequest(ts.Mapper, relays.AwaitPersonTurnCompletedRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call_id=str(call.identity))


class MapToHangUpRequest(ts.Mapper, relays.HangUpRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToRecordCallRequest(ts.Mapper, relays.RecordCallRequest):
    def __init__(self, call: domain.Call) -> None:
        super().__init__(call=call)


class MapToConductCallResponse(ts.Mapper, relays.ConductCallResponse):
    def __init__(self, record_call_response: relays.RecordCallResponse) -> None:
        super().__init__(call_id=record_call_response.call_id)


class CallOrchestrator(ts.Orchestrator):
    def __init__(
        self,
        dialing_actions_relay: relays.DialingActionsRelay,
        call_orchestrator_signal_relay: relays.CallOrchestratorSignalRelay,
        speech_actions_relay: relays.SpeechActionsRelay,
        call_actions_relay: relays.CallActionsRelay,
    ) -> None:
        self._dialing_actions_relay = dialing_actions_relay
        self._call_orchestrator_signal_relay = call_orchestrator_signal_relay
        self._speech_actions_relay = speech_actions_relay
        self._call_actions_relay = call_actions_relay

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        call = conduct_call_request.call
        await self._dialing_actions_relay.run_dial_person(MapToDialPersonRequest(call))
        await self._call_orchestrator_signal_relay.await_person_joined(MapToAwaitPersonJoinedRequest(call))
        await self._speech_actions_relay.run_say_utterance(MapToSayUtteranceRequest(call, call.question))
        await_person_turn_completed_response = await self._call_orchestrator_signal_relay.await_person_turn_completed(MapToAwaitPersonTurnCompletedRequest(call))
        call.person_said(domain.Utterance(await_person_turn_completed_response.text))
        await self._speech_actions_relay.run_say_utterance(MapToSayUtteranceRequest(call, call.greeting))
        await self._dialing_actions_relay.run_hang_up(MapToHangUpRequest(call))
        record_call_response = await self._call_actions_relay.run_record_call(MapToRecordCallRequest(call))
        return MapToConductCallResponse(record_call_response)
