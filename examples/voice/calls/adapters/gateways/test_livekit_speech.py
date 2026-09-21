from __future__ import annotations

import base64
import json
import typing

import tesser.testing as ts
import livekit.rtc as livekit_rtc

import calls.adapters.gateways as gateways
import calls.application.ports as ports


@ts.fake
class FakeLocalParticipant:  # tesser:debt TB072
    def __init__(self, reply: str, performed: list[dict[str, str]]) -> None:
        self._reply = reply
        self._performed = performed

    async def perform_rpc(self, destination_identity: str, method: str, payload: str, response_timeout: float) -> str:
        self._performed.append({"destination_identity": destination_identity, "method": method, "payload": payload})
        return self._reply


@ts.fake
class FakeRoom:  # tesser:debt TB072
    reply: typing.ClassVar[str] = ""
    connected: typing.ClassVar[list[tuple[str, str]]] = []
    performed: typing.ClassVar[list[dict[str, str]]] = []
    disconnected: typing.ClassVar[list[bool]] = []

    def __init__(self) -> None:
        self.local_participant = FakeLocalParticipant(FakeRoom.reply, FakeRoom.performed)

    async def connect(self, url: str, token: str) -> None:
        FakeRoom.connected.append((url, token))

    async def disconnect(self) -> None:
        FakeRoom.disconnected.append(True)


class TestLivekitAgentRpc:
    async def test_the_agent_in_the_room_is_asked_the_method_with_the_payload(self) -> None:
        FakeRoom.reply = ""
        FakeRoom.performed = []
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        await livekit_agent_rpc.ask("c7", "say", "hello")

        assert [
            (performed["destination_identity"], performed["method"], performed["payload"])
            for performed in FakeRoom.performed
        ] == [("agent", "say", "hello")]

    async def test_the_room_joined_is_the_one_named_for_the_call(self) -> None:
        FakeRoom.reply = ""
        FakeRoom.connected = []
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        await livekit_agent_rpc.ask("c7", "say", "hello")
        token = FakeRoom.connected[-1][1].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))

        assert claims["video"]["room"] == "c7"

    async def test_the_room_is_left_once_the_agent_has_replied(self) -> None:
        FakeRoom.reply = ""
        FakeRoom.disconnected = []
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        await livekit_agent_rpc.ask("c7", "say", "hello")

        assert FakeRoom.disconnected == [True]

    async def test_the_agents_reply_is_answered(self) -> None:
        FakeRoom.reply = "ok"
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        reply = await livekit_agent_rpc.ask("c7", "say", "hello")

        assert reply == "ok"


class TestLivekitSpeech:
    async def test_saying_an_utterance_asks_the_agent_to_say_the_text(self) -> None:
        FakeRoom.reply = ""
        FakeRoom.performed = []

        await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(
                typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
            )
        ).say_utterance(ports.SayUtteranceRequest(call_id="c7", text="Nice to meet you, Grace. Goodbye."))

        assert [
            (performed["destination_identity"], performed["method"], performed["payload"])
            for performed in FakeRoom.performed
        ] == [("agent", "say", "Nice to meet you, Grace. Goodbye.")]

    async def test_saying_an_utterance_answers_the_call_it_spoke_on(self) -> None:
        FakeRoom.reply = ""

        say_utterance_response = await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(
                typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
            )
        ).say_utterance(ports.SayUtteranceRequest(call_id="c7", text="hello"))

        assert say_utterance_response.call_id == "c7"
