from __future__ import annotations

import asyncio
import json
import os
import socket
import typing
import uuid

import tesser.testing as ts
import httpx
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import restate
import restate.client as restate_client

import calls.adapters.activities as activities
import calls.adapters.workflows as workflows
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallApplicationClient(client.CallApplicationClient):
    def __init__(self) -> None:
        self.recorded: list[relays.RecordCallRequest] = []

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


@ts.fake
class FakeDialingApplicationClient(client.DialingApplicationClient):
    def __init__(self) -> None:
        self.dialed: list[relays.DialPersonRequest] = []

    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        self.dialed.append(dial_person_request)
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    def __init__(self) -> None:
        self.said: list[str] = []

    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        self.said.append(say_utterance_request.text)
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.helper
def conduct_call_request(call_id: str = "c7") -> relays.ConductCallRequest:
    return relays.ConductCallRequest(call=domain.Call(domain.CallSpec(call_id=call_id, person_name="")))


class TestRestateConductCall:
    async def test_conduct_call_reaches_the_handler_it_holds_and_waits_on_the_promise_the_relays_name(
        self,
    ) -> None:
        call_id = str(uuid.uuid4())
        fake_dialing_application_client = FakeDialingApplicationClient()
        suffix = uuid.uuid4().hex
        dialing_actions_service = restate.Service(f"DialingActions{suffix}")
        call_orchestrator_workflow = restate.Workflow(f"CallOrchestrator{suffix}")
        restate_conduct_call = workflows.RestateConductCall(
            call_orchestrator_workflow,
            activities.RestateRecordCall(restate.Service("CallActions"), FakeCallApplicationClient()),
            activities.RestateDialPerson(dialing_actions_service, fake_dialing_application_client),
            activities.RestateHangUp(dialing_actions_service, fake_dialing_application_client),
            activities.RestateSayUtterance(restate.Service("SpeechActions"), FakeSpeechApplicationClient()),
        )
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([dialing_actions_service, call_orchestrator_workflow])),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        try:
            for _ in range(50):
                registered = await admin.post(
                    "/deployments",
                    json={"uri": f"http://{os.environ['VOICE_CALLBACK_HOST']}:{port}", "force": True},
                )
                if registered.is_success:
                    break
                await asyncio.sleep(0.1)
            assert registered.is_success, registered.text

            async with httpx.AsyncClient(base_url=os.environ["RESTATE_URL"], timeout=30.0) as async_client:
                sent = await restate_client.Client(async_client).workflow_send(
                    restate_conduct_call.handler, key=call_id, arg=conduct_call_request(call_id=call_id)
                )
            called: list[tuple[str, str]] = []
            awaited: list[str] = []
            for _ in range(100):
                invoked = await admin.post(
                    "/query",
                    headers={"accept": "application/json"},
                    json={
                        "query": "SELECT target, completion_result FROM sys_invocation "
                        f"WHERE invoked_by_id = '{sent.invocation_id}' ORDER BY created_at"
                    },
                )
                journaled = await admin.post(
                    "/query",
                    headers={"accept": "application/json"},
                    json={
                        "query": "SELECT entry_lite_json FROM sys_journal "
                        f"WHERE id = '{sent.invocation_id}' AND entry_type = 'Command: GetPromise' ORDER BY index"
                    },
                )
                called = [(row["target"], row.get("completion_result", "")) for row in invoked.json()["rows"]]
                awaited = [
                    json.loads(row["entry_lite_json"])["Command"]["GetPromise"]["key"] for row in journaled.json()["rows"]
                ]
                if awaited:
                    break
                await asyncio.sleep(0.05)
            await admin.patch(f"/invocations/{sent.invocation_id}/kill")

            assert called == [(f"DialingActions{suffix}/dial_person", "success")]
            assert [str(dialed.call.identity) for dialed in fake_dialing_application_client.dialed] == [call_id]
            assert awaited == [relays.PERSON_JOINED_PROMISE]
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)
