from __future__ import annotations

import json

import tesser.adapters as ts
import livekit.agents.inference as livekit_inference
import livekit.agents.llm as livekit_llm

import calls.application.ports as ports


class MapToInterpretTurnResponse(ts.Mapper, ports.InterpretTurnResponse):
    def __init__(self, call_id: str, output: str) -> None:
        payload = json.loads(output)
        if not (
            isinstance(payload, dict)
            and isinstance(payload.get("person_names"), list)
            and all(isinstance(name, str) for name in payload["person_names"])
        ):
            raise ValueError("interpretation must contain a list of person names")
        super().__init__(call_id=call_id, person_names=tuple(payload["person_names"]))


class LivekitInterpretation(ts.Gateway):
    def __init__(self, llm: livekit_inference.LLM) -> None:
        self._llm = llm

    async def interpret_turn(self, interpret_turn_request: ports.InterpretTurnRequest) -> ports.InterpretTurnResponse:
        chat_context = livekit_llm.ChatContext.empty()
        chat_context.add_message(role="system", content=interpret_turn_request.instructions)
        for turn in interpret_turn_request.turns:
            chat_context.add_message(role="assistant" if turn.spoken_by == "agent" else "user", content=turn.text)
        async with self._llm.chat(
            chat_ctx=chat_context, extra_kwargs={"response_format": {"type": "json_object"}}
        ) as stream:
            output = "".join([text async for text in stream.to_str_iterable()])
        return MapToInterpretTurnResponse(interpret_turn_request.call_id, output)
