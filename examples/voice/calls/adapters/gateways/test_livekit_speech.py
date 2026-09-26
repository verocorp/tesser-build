from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import tesser.testing as ts
import livekit.api as livekit_api
import livekit.rtc as livekit_rtc

import calls.adapters.gateways as gateways
import calls.application.ports as ports


@ts.peer
class RecordingRpcPeer:

    def __init__(self, received: asyncio.Queue[livekit_rtc.RpcInvocationData], reply: str) -> None:
        self._received = received
        self._reply = reply

    async def __call__(self, rpc_invocation_data: livekit_rtc.RpcInvocationData) -> str:
        await self._received.put(rpc_invocation_data)
        return self._reply


class TestLivekitAgentRpc:

    async def test_the_agent_in_the_room_is_asked_the_method_with_the_payload(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                await livekit_agent_rpc.ask(call_id, "say", "hello")
                invocation = received.get_nowait()
                assert invocation.method == "say"
                assert invocation.payload == "hello"
                assert invocation.caller_identity == f"speech-{call_id}"
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_the_room_joined_is_the_one_named_for_the_call(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                await livekit_agent_rpc.ask(call_id, "say", "hello")
                assert agent_room.name == call_id
                assert received.get_nowait().caller_identity == f"speech-{call_id}"
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_the_room_is_left_once_the_agent_has_replied(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                await livekit_agent_rpc.ask(call_id, "say", "hello")
                assert received.qsize() == 1
                participants = await livekit.room.list_participants(livekit_api.ListParticipantsRequest(room=call_id))
                assert [participant.identity for participant in participants.participants] == ["agent"]
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_the_room_is_left_when_joining_it_fails(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                with pytest.raises(livekit_rtc.ConnectError):
                    await gateways.LivekitAgentRpc(url, key, "invalid-secret", "agent").ask(call_id, "say", "hello")
                assert received.empty()
                participants = await livekit.room.list_participants(livekit_api.ListParticipantsRequest(room=call_id))
                assert [participant.identity for participant in participants.participants] == ["agent"]
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_the_agents_reply_is_answered(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                agent_room.local_participant.register_rpc_method("reply", RecordingRpcPeer(received, "ok"))
                reply = await livekit_agent_rpc.ask(call_id, "reply", "hello")
                assert reply == "ok"
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_the_room_is_left_when_the_rpc_fails(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                with pytest.raises(livekit_rtc.RpcError) as raised:
                    await livekit_agent_rpc.ask(call_id, "unknown", "hello")
                assert raised.value.code == livekit_rtc.RpcError.ErrorCode.UNSUPPORTED_METHOD
                participants = await livekit.room.list_participants(livekit_api.ListParticipantsRequest(room=call_id))
                assert [participant.identity for participant in participants.participants] == ["agent"]
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))


class TestLivekitSpeech:

    async def test_saying_an_utterance_asks_the_agent_to_say_the_text(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                await gateways.LivekitSpeech(livekit_agent_rpc).say_utterance(
                    ports.SayUtteranceRequest(call_id=call_id, text="Nice to meet you, Grace. Goodbye.")
                )
                invocation = received.get_nowait()
                assert invocation.method == "say"
                assert invocation.payload == "Nice to meet you, Grace. Goodbye."
                assert invocation.caller_identity == f"speech-{call_id}"
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))

    async def test_saying_an_utterance_answers_the_call_it_spoke_on(self) -> None:
        call_id = f"speech-{uuid.uuid4()}"
        url, key, secret = os.environ["LIVEKIT_URL"], os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"]
        agent_room = livekit_rtc.Room()
        token = (
            livekit_api.AccessToken(key, secret)
            .with_identity("agent")
            .with_grants(livekit_api.VideoGrants(room_join=True, room=call_id))
            .to_jwt()
        )
        received: asyncio.Queue[livekit_rtc.RpcInvocationData] = asyncio.Queue()
        async with livekit_api.LiveKitAPI(url, key, secret) as livekit:
            await agent_room.connect(url, token)
            try:
                agent_room.local_participant.register_rpc_method("say", RecordingRpcPeer(received, ""))
                livekit_agent_rpc = gateways.LivekitAgentRpc(url, key, secret, "agent")
                say_utterance_response = await gateways.LivekitSpeech(livekit_agent_rpc).say_utterance(
                    ports.SayUtteranceRequest(call_id=call_id, text="hello")
                )
                assert say_utterance_response.call_id == call_id
            finally:
                await agent_room.disconnect()
                await livekit.room.delete_room(livekit_api.DeleteRoomRequest(room=call_id))
