from __future__ import annotations

import tesser.application as ts

import calls.application.ports as ports
import calls.application.relays as relays
import calls.domain as domain


class MapToInterpretedConversationTurn(ts.Mapper, ports.InterpretedConversationTurn):
    def __init__(self, turn: domain.Turn) -> None:
        super().__init__(spoken_by=str(turn.speaker), text=" ".join(str(u) for u in turn.utterances))


class MapToInterpretTurnRequest(ts.Mapper, ports.InterpretTurnRequest):
    def __init__(self, interpret_turn_request: relays.InterpretTurnRequest) -> None:
        super().__init__(
            call_id=str(interpret_turn_request.call.identity),
            instructions=str(interpret_turn_request.call.listening_instructions),
            turns=tuple(
                MapToInterpretedConversationTurn(turn) for turn in interpret_turn_request.call.conversation.turns
            ),
        )


class MapToInterpretTurnResponse(ts.Mapper, relays.InterpretTurnResponse):
    def __init__(self, interpret_turn_response: ports.InterpretTurnResponse) -> None:
        super().__init__(call_id=interpret_turn_response.call_id, person_names=interpret_turn_response.person_names)


class InterpretationActions(ts.Actions):
    def __init__(self, interpretation: ports.Interpretation) -> None:
        self._interpretation = interpretation

    async def interpret_turn(self, interpret_turn_request: relays.InterpretTurnRequest) -> relays.InterpretTurnResponse:
        return MapToInterpretTurnResponse(
            await self._interpretation.interpret_turn(MapToInterpretTurnRequest(interpret_turn_request))
        )
