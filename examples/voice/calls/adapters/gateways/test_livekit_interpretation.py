from __future__ import annotations

import json

import aiohttp.web as aiohttp_web
import pytest
import livekit.agents.inference as livekit_inference
import tesser.testing as ts

import calls.adapters.gateways as gateways
import calls.application.ports as ports


@ts.fake
class InterpretationEndpoint:  # tesser:debt TB072
    def __init__(self, output: str) -> None:
        self._output = output
        self.requests: list[dict[str, object]] = []
        self._app = aiohttp_web.Application()
        self._app.router.add_post("/v1/chat/completions", self.respond)  # tesser:debt TB051
        self._runner = aiohttp_web.AppRunner(self._app)

    async def start(self) -> str:
        await self._runner.setup()
        await aiohttp_web.TCPSite(self._runner, "127.0.0.1", 0).start()
        return f"http://127.0.0.1:{self._runner.addresses[0][1]}/v1"

    async def close(self) -> None:
        await self._runner.cleanup()

    async def respond(self, request: aiohttp_web.Request) -> aiohttp_web.Response:
        self.requests.append(await request.json())
        chunk = {
            "id": "chat-1",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "test",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": self._output}, "finish_reason": "stop"}],
        }
        return aiohttp_web.Response(
            text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n", content_type="text/event-stream"
        )


class TestLivekitInterpretation:
    async def test_the_real_sdk_sends_listening_content_and_returns_structured_names(self) -> None:
        interpretation_endpoint = InterpretationEndpoint('{"person_names": ["Grace"]}')  # tesser:debt TB085
        url = await interpretation_endpoint.start()
        llm = livekit_inference.LLM(
            "openai/gpt-4.1-mini", base_url=url, api_key="test", api_secret="test-secret-that-is-at-least-32-bytes"
        )
        try:
            interpret_turn_response = await gateways.LivekitInterpretation(llm).interpret_turn(
                ports.InterpretTurnRequest(
                    call_id="c7",
                    instructions="Extract names; do not speak.",
                    turns=(ports.InterpretedConversationTurn(spoken_by="person", text="My name is Grace"),),
                )
            )
            assert interpret_turn_response.call_id == "c7"
            assert interpret_turn_response.person_names == ("Grace",)
            assert interpretation_endpoint.requests[0]["messages"] == [
                {"role": "system", "content": "Extract names; do not speak."},
                {"role": "user", "content": "My name is Grace"},
            ]
            assert interpretation_endpoint.requests[0]["response_format"] == {"type": "json_object"}
        finally:
            await llm.aclose()
            await interpretation_endpoint.close()

    async def test_malformed_interpretation_is_rejected(self) -> None:
        interpretation_endpoint = InterpretationEndpoint('{"person_names": [42]}')  # tesser:debt TB085
        url = await interpretation_endpoint.start()
        llm = livekit_inference.LLM(
            "openai/gpt-4.1-mini", base_url=url, api_key="test", api_secret="test-secret-that-is-at-least-32-bytes"
        )
        try:
            with pytest.raises(ValueError, match="list of person names"):
                await gateways.LivekitInterpretation(llm).interpret_turn(
                    ports.InterpretTurnRequest(call_id="c7", instructions="Extract names.", turns=())
                )
        finally:
            await llm.aclose()
            await interpretation_endpoint.close()
