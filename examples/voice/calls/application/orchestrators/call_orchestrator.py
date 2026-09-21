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


class MapToAwaitPersonTurnRequest(ts.Mapper, relays.AwaitPersonTurnRequest):
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
        dialing_relay: relays.DialingRelay,
        person_relay: relays.PersonRelay,
        say_utterance_relay: relays.SayUtteranceRelay,
        record_call_relay: relays.RecordCallRelay,
    ) -> None:
        self._dialing_relay = dialing_relay
        self._person_relay = person_relay
        self._say_utterance_relay = say_utterance_relay
        self._record_call_relay = record_call_relay

    async def conduct_call(self, conduct_call_request: relays.ConductCallRequest) -> relays.ConductCallResponse:
        call = conduct_call_request.call
        await self._dialing_relay.run_dial_person(MapToDialPersonRequest(call))
        await self._person_relay.await_person_joined(MapToAwaitPersonJoinedRequest(call))
        await self._say_utterance_relay.run_say_utterance(MapToSayUtteranceRequest(call, call.question))
        await_person_turn_response = await self._person_relay.await_person_turn(MapToAwaitPersonTurnRequest(call))
        call.person_said(domain.Utterance(await_person_turn_response.text))
        await self._say_utterance_relay.run_say_utterance(MapToSayUtteranceRequest(call, call.greeting))
        await self._dialing_relay.run_hang_up(MapToHangUpRequest(call))
        record_call_response = await self._record_call_relay.run_record_call(MapToRecordCallRequest(call))
        return MapToConductCallResponse(record_call_response)
