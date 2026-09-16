from __future__ import annotations

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

    async def perform_rpc(
        self, destination_identity: str, method: str, payload: str, response_timeout: float
    ) -> str:
        self._performed.append({"destination_identity": destination_identity, "method": method, "payload": payload})
        return self._reply


@ts.fake
class FakeRoom:  # tesser:debt TB072

    reply: typing.ClassVar[str] = "[]"
    connected: typing.ClassVar[list[tuple[str, str]]] = []
    performed: typing.ClassVar[list[dict[str, str]]] = []
    disconnected: typing.ClassVar[list[bool]] = []

    def __init__(self) -> None:
        self.local_participant = FakeLocalParticipant(FakeRoom.reply, FakeRoom.performed)

    async def connect(self, url: str, token: str) -> None:
        FakeRoom.connected.append((url, token))

    async def disconnect(self) -> None:
        FakeRoom.disconnected.append(True)


@ts.helper
def speak_turn_request(
    call_id: str = "c7", persona: str = "a friendly receptionist", instructions: str = "ask for their name"
) -> ports.SpeakTurnRequest:
    return ports.SpeakTurnRequest(
        call_id=call_id,
        persona=persona,
        turns=(
            ports.SpokenTurn(spoken_by=ports.SpokenBy.AGENT, text="hi, may I have your name?"),
            ports.SpokenTurn(spoken_by=ports.SpokenBy.PERSON, text="my name is Ada"),
        ),
        instructions=instructions,
    )


class TestLivekitAgentRpc:

    async def test_the_agent_in_the_room_named_for_the_call_is_asked(self) -> None:
        FakeRoom.reply = "[]"
        FakeRoom.performed = []
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        await livekit_agent_rpc.ask("c7", "speak_turn", "{}")

        assert [(p["destination_identity"], p["method"], p["payload"]) for p in FakeRoom.performed] == [
            ("agent", "speak_turn", "{}")
        ]

    async def test_the_room_is_left_once_the_agent_has_replied(self) -> None:
        FakeRoom.reply = "[]"
        FakeRoom.disconnected = []
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        await livekit_agent_rpc.ask("c7", "speak_turn", "{}")

        assert FakeRoom.disconnected == [True]

    async def test_the_agents_reply_is_answered(self) -> None:
        FakeRoom.reply = '["hi"]'
        livekit_agent_rpc = gateways.LivekitAgentRpc(
            typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
        )

        reply = await livekit_agent_rpc.ask("c7", "speak_turn", "{}")

        assert reply == '["hi"]'


class TestLivekitSpeech:

    async def test_speaking_a_turn_asks_the_agent_to_speak_a_turn(self) -> None:
        FakeRoom.reply = "[]"
        FakeRoom.performed = []

        await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).speak_turn(speak_turn_request(call_id="c7"))

        assert [(p["destination_identity"], p["method"]) for p in FakeRoom.performed] == [("agent", "speak_turn")]

    async def test_the_agent_is_handed_the_persona_the_turns_so_far_and_the_instructions(self) -> None:
        FakeRoom.reply = "[]"
        FakeRoom.performed = []

        await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).speak_turn(speak_turn_request(persona="a friendly receptionist", instructions="ask"))
        payload = json.loads(FakeRoom.performed[-1]["payload"])

        assert payload["persona"] == "a friendly receptionist"
        assert payload["turns"] == [
            {"spoken_by": "agent", "text": "hi, may I have your name?"},
            {"spoken_by": "person", "text": "my name is Ada"},
        ]
        assert payload["instructions"] == "ask"
        assert [tool["name"] for tool in payload["tools"]] == ["person_gave_name"]

    async def test_what_the_agent_said_comes_back_as_the_turns_text(self) -> None:
        FakeRoom.reply = json.dumps(
            [{"type": "message", "text": "Nice to meet you."}, {"type": "message", "text": "Thanks, Ada."}]
        )

        speak_turn_response = await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).speak_turn(speak_turn_request())

        assert speak_turn_response.text == "Nice to meet you. Thanks, Ada."

    async def test_a_name_the_agent_recorded_comes_back_as_a_person_name(self) -> None:
        FakeRoom.reply = json.dumps(
            [
                {"type": "function_call", "name": "person_gave_name", "arguments": '{"name": "Ada"}'},
                {"type": "function_call_output", "name": "person_gave_name", "output": "recorded"},
                {"type": "message", "text": "Thanks, Ada."},
            ]
        )

        speak_turn_response = await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).speak_turn(speak_turn_request())

        assert speak_turn_response.person_names == ("Ada",)

    async def test_a_turn_with_no_name_recorded_carries_no_person_name(self) -> None:
        FakeRoom.reply = json.dumps([{"type": "message", "text": "Sorry, what was that?"}])

        speak_turn_response = await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).speak_turn(speak_turn_request())

        assert speak_turn_response.person_names == ()

    async def test_a_tool_call_whose_arguments_cannot_be_read_records_no_name(self) -> None:
        for arguments in ("{bad", None, '{"name": 42}'):
            FakeRoom.reply = json.dumps(
                [
                    {"type": "function_call", "name": "person_gave_name", "arguments": arguments},
                    {"type": "message", "text": "sorry, could you repeat that?"},
                ]
            )

            speak_turn_response = await gateways.LivekitSpeech(
                gateways.LivekitAgentRpc(
                    typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent"
                )
            ).speak_turn(speak_turn_request())

            assert (speak_turn_response.text, speak_turn_response.person_names) == ("sorry, could you repeat that?", ())

    async def test_ending_the_persons_turn_asks_the_agent_to_end_it(self) -> None:
        FakeRoom.reply = ""
        FakeRoom.performed = []

        await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).end_person_turn(ports.EndPersonTurnRequest(call_id="c7"))

        assert [(p["destination_identity"], p["method"], p["payload"]) for p in FakeRoom.performed] == [
            ("agent", "end_person_turn", '{"call_id": "c7"}')
        ]

    async def test_ending_the_persons_turn_answers_the_call_id(self) -> None:
        FakeRoom.reply = ""

        end_person_turn_response = await gateways.LivekitSpeech(
            gateways.LivekitAgentRpc(typing.cast(type[livekit_rtc.Room], FakeRoom), "ws://livekit", "key", "secret", "agent")
        ).end_person_turn(ports.EndPersonTurnRequest(call_id="c7"))

        assert end_person_turn_response.call_id == "c7"
