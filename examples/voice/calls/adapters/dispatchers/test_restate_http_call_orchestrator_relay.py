from __future__ import annotations

import asyncio
import os
import socket
import typing
import uuid

import tesser.testing as ts
import pytest
import httpx
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import restate
import restate.client as restate_client

import calls.adapters.activities as activities
import calls.adapters.dispatchers as dispatchers
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
    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
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
def call_spec(call_id: str = "c7", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


@ts.helper
def conduct_call_request(
    call: domain.Call,
) -> relays.ConductCallRequest:
    return relays.ConductCallRequest(call=call)


class TestRestateHttpCallOrchestratorRelay:
    async def test_a_call_conducted_through_the_engine_records_the_name_the_person_said(self) -> None:
        call_id = str(uuid.uuid4())
        fake_call_application_client = FakeCallApplicationClient()
        fake_dialing_application_client = FakeDialingApplicationClient()
        fake_speech_application_client = FakeSpeechApplicationClient()
        suffix = uuid.uuid4().hex
        call_actions_service = restate.Service(f"CallActions{suffix}")
        dialing_actions_service = restate.Service(f"DialingActions{suffix}")
        speech_actions_service = restate.Service(f"SpeechActions{suffix}")
        call_orchestrator_workflow = restate.Workflow(f"CallOrchestrator{suffix}")
        restate_conduct_call = workflows.RestateConductCall(
            call_orchestrator_workflow,
            activities.RestateRecordCall(call_actions_service, fake_call_application_client),
            activities.RestateDialPerson(dialing_actions_service, fake_dialing_application_client),
            activities.RestateHangUp(dialing_actions_service, fake_dialing_application_client),
            activities.RestateSayUtterance(speech_actions_service, fake_speech_application_client),
        )
        restate_person_joined = dispatchers.RestatePersonJoined(call_orchestrator_workflow)
        restate_person_turn_completed = dispatchers.RestatePersonTurnCompleted(call_orchestrator_workflow)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([call_actions_service, dialing_actions_service, speech_actions_service, call_orchestrator_workflow])),
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

            restate_http_call_orchestrator_relay = dispatchers.RestateHttpCallOrchestratorRelay(
                os.environ["RESTATE_URL"],
                restate_conduct_call,
                restate_person_joined,
                restate_person_turn_completed,
            )
            conducting = asyncio.create_task(
                restate_http_call_orchestrator_relay.run_conduct_call(conduct_call_request(call=domain.Call(call_spec(call_id=call_id))))
            )
            started: list[str] = []
            for _ in range(100):
                stated = await admin.post(
                    "/query",
                    headers={"accept": "application/json"},
                    json={
                        "query": "SELECT key FROM state "
                        f"WHERE service_name = '{call_orchestrator_workflow.name}' AND service_key = '{call_id}'"
                    },
                )
                started = [row["key"] for row in stated.json()["rows"]]
                if started:
                    break
                await asyncio.sleep(0.05)
            await restate_http_call_orchestrator_relay.run_person_joined(relays.PersonJoinedRequest(call_id=call_id))
            await restate_http_call_orchestrator_relay.run_person_turn_completed(
                relays.PersonTurnCompletedRequest(call_id=call_id, text="Grace")
            )
            conduct_call_response = await conducting
            invoked = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT target, completion_result FROM sys_invocation "
                    f"WHERE invoked_by_target = '{call_orchestrator_workflow.name}/{call_id}/conduct_call' "
                    "ORDER BY created_at"
                },
            )

            assert started == [relays.CONDUCT_CALL_STATE]
            assert conduct_call_response.call_id == call_id
            assert [str(recorded.call.person_name) for recorded in fake_call_application_client.recorded] == ["Grace"]
            assert fake_speech_application_client.said == [
                "Hello. Please tell me your first name.",
                "Nice to meet you, Grace. Goodbye.",
            ]
            assert [(row["target"], row["completion_result"]) for row in invoked.json()["rows"]] == [
                (f"DialingActions{suffix}/dial_person", "success"),
                (f"SpeechActions{suffix}/say_utterance", "success"),
                (f"SpeechActions{suffix}/say_utterance", "success"),
                (f"DialingActions{suffix}/hang_up", "success"),
                (f"CallActions{suffix}/record_call", "success"),
            ]
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)

    async def test_concurrent_joins_and_completed_turns_for_one_call_are_all_acknowledged(self) -> None:
        call_id = str(uuid.uuid4())
        suffix = uuid.uuid4().hex
        call_actions_service = restate.Service(f"CallActions{suffix}")
        dialing_actions_service = restate.Service(f"DialingActions{suffix}")
        speech_actions_service = restate.Service(f"SpeechActions{suffix}")
        call_orchestrator_workflow = restate.Workflow(f"CallOrchestrator{suffix}")
        restate_conduct_call = workflows.RestateConductCall(
            call_orchestrator_workflow,
            activities.RestateRecordCall(call_actions_service, FakeCallApplicationClient()),
            activities.RestateDialPerson(dialing_actions_service, FakeDialingApplicationClient()),
            activities.RestateHangUp(dialing_actions_service, FakeDialingApplicationClient()),
            activities.RestateSayUtterance(speech_actions_service, FakeSpeechApplicationClient()),
        )
        restate_person_joined = dispatchers.RestatePersonJoined(call_orchestrator_workflow)
        restate_person_turn_completed = dispatchers.RestatePersonTurnCompleted(call_orchestrator_workflow)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([call_actions_service, dialing_actions_service, speech_actions_service, call_orchestrator_workflow])),
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

            restate_http_call_orchestrator_relay = dispatchers.RestateHttpCallOrchestratorRelay(
                os.environ["RESTATE_URL"],
                restate_conduct_call,
                restate_person_joined,
                restate_person_turn_completed,
            )
            conducting = asyncio.create_task(
                restate_http_call_orchestrator_relay.run_conduct_call(conduct_call_request(call=domain.Call(call_spec(call_id=call_id))))
            )
            started: list[str] = []
            for _ in range(100):
                stated = await admin.post(
                    "/query",
                    headers={"accept": "application/json"},
                    json={
                        "query": "SELECT key FROM state "
                        f"WHERE service_name = '{call_orchestrator_workflow.name}' AND service_key = '{call_id}'"
                    },
                )
                started = [row["key"] for row in stated.json()["rows"]]
                if started:
                    break
                await asyncio.sleep(0.05)
            person_joined_responses = await asyncio.gather(
                *(
                    restate_http_call_orchestrator_relay.run_person_joined(
                        relays.PersonJoinedRequest(call_id=call_id)
                    )
                    for _ in range(8)
                )
            )
            person_turn_completed_responses = await asyncio.gather(
                *(
                    restate_http_call_orchestrator_relay.run_person_turn_completed(
                        relays.PersonTurnCompletedRequest(call_id=call_id, text=f"turn {turn}")
                    )
                    for turn in range(8)
                )
            )
            conduct_call_response = await conducting

            assert started == [relays.CONDUCT_CALL_STATE]
            assert [person_joined_response.call_id for person_joined_response in person_joined_responses] == [
                call_id
            ] * 8
            assert [
                person_turn_completed_response.call_id
                for person_turn_completed_response in person_turn_completed_responses
            ] == [call_id] * 8
            assert conduct_call_response.call_id == call_id
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)

    async def test_the_key_is_encoded_so_a_call_id_cannot_reshape_the_path(self) -> None:
        call_id = "../admin?x=1#f-" + str(uuid.uuid4())
        suffix = uuid.uuid4().hex
        call_actions_service = restate.Service(f"CallActions{suffix}")
        dialing_actions_service = restate.Service(f"DialingActions{suffix}")
        speech_actions_service = restate.Service(f"SpeechActions{suffix}")
        call_orchestrator_workflow = restate.Workflow(f"CallOrchestrator{suffix}")
        restate_conduct_call = workflows.RestateConductCall(
            call_orchestrator_workflow,
            activities.RestateRecordCall(call_actions_service, FakeCallApplicationClient()),
            activities.RestateDialPerson(dialing_actions_service, FakeDialingApplicationClient()),
            activities.RestateHangUp(dialing_actions_service, FakeDialingApplicationClient()),
            activities.RestateSayUtterance(speech_actions_service, FakeSpeechApplicationClient()),
        )
        restate_person_joined = dispatchers.RestatePersonJoined(call_orchestrator_workflow)
        restate_person_turn_completed = dispatchers.RestatePersonTurnCompleted(call_orchestrator_workflow)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([call_actions_service, dialing_actions_service, speech_actions_service, call_orchestrator_workflow])),
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

            restate_http_call_orchestrator_relay = dispatchers.RestateHttpCallOrchestratorRelay(
                os.environ["RESTATE_URL"],
                restate_conduct_call,
                restate_person_joined,
                restate_person_turn_completed,
            )
            conducting = asyncio.create_task(
                restate_http_call_orchestrator_relay.run_conduct_call(conduct_call_request(call=domain.Call(call_spec(call_id=call_id))))
            )
            started: list[str] = []
            for _ in range(100):
                stated = await admin.post(
                    "/query",
                    headers={"accept": "application/json"},
                    json={
                        "query": "SELECT key FROM state "
                        f"WHERE service_name = '{call_orchestrator_workflow.name}' AND service_key = '{call_id}'"
                    },
                )
                started = [row["key"] for row in stated.json()["rows"]]
                if started:
                    break
                await asyncio.sleep(0.05)
            person_joined_response = await restate_http_call_orchestrator_relay.run_person_joined(
                relays.PersonJoinedRequest(call_id=call_id)
            )
            promised = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT key FROM sys_promise "
                    f"WHERE service_name = '{call_orchestrator_workflow.name}' AND service_key = '{call_id}'"
                },
            )
            await restate_http_call_orchestrator_relay.run_person_turn_completed(
                relays.PersonTurnCompletedRequest(call_id=call_id, text="Grace")
            )
            conduct_call_response = await conducting

            assert started == [relays.CONDUCT_CALL_STATE]
            assert person_joined_response.call_id == call_id
            assert conduct_call_response.call_id == call_id
            assert [row["key"] for row in promised.json()["rows"]] == [relays.PERSON_JOINED_PROMISE]
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)


class TestRestatePersonJoined:
    async def test_restate_refuses_a_person_joined_signal_for_a_foreign_key_or_a_call_not_yet_started(self) -> None:
        call_id = str(uuid.uuid4())
        call_orchestrator_workflow = restate.Workflow(f"CallOrchestrator{uuid.uuid4().hex}")
        workflows.RestateConductCall(
            call_orchestrator_workflow,
            activities.RestateRecordCall(restate.Service("CallActions"), FakeCallApplicationClient()),
            activities.RestateDialPerson(restate.Service("DialingActions"), FakeDialingApplicationClient()),
            activities.RestateHangUp(restate.Service("DialingActions"), FakeDialingApplicationClient()),
            activities.RestateSayUtterance(restate.Service("SpeechActions"), FakeSpeechApplicationClient()),
        )
        restate_person_joined = dispatchers.RestatePersonJoined(call_orchestrator_workflow)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([call_orchestrator_workflow])),
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
                with pytest.raises(restate.HttpError) as refused:
                    await restate_client.Client(async_client).workflow_call(
                        restate_person_joined.handler, key=f"other-{uuid.uuid4()}", arg=relays.PersonJoinedRequest(call_id="c7")
                    )
                with pytest.raises(restate.HttpError) as early:
                    await restate_client.Client(async_client).workflow_call(
                        restate_person_joined.handler, key=call_id, arg=relays.PersonJoinedRequest(call_id=call_id)
                    )
            promised = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT key FROM sys_promise "
                    f"WHERE service_name = '{call_orchestrator_workflow.name}' AND service_key = '{call_id}'"
                },
            )

            assert refused.value.status_code == 400
            assert "a message names the call its workflow is keyed by" in (refused.value.body or "")
            assert early.value.status_code == 412
            assert "no call has started under this key" in (early.value.body or "")
            assert promised.json()["rows"] == []
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()



class TestRestatePersonTurnCompleted:
    async def test_restate_refuses_a_person_turn_completed_signal_for_a_foreign_key_or_a_call_not_yet_started(self) -> None:
        call_id = str(uuid.uuid4())
        call_orchestrator_workflow = restate.Workflow(f"CallOrchestrator{uuid.uuid4().hex}")
        workflows.RestateConductCall(
            call_orchestrator_workflow,
            activities.RestateRecordCall(restate.Service("CallActions"), FakeCallApplicationClient()),
            activities.RestateDialPerson(restate.Service("DialingActions"), FakeDialingApplicationClient()),
            activities.RestateHangUp(restate.Service("DialingActions"), FakeDialingApplicationClient()),
            activities.RestateSayUtterance(restate.Service("SpeechActions"), FakeSpeechApplicationClient()),
        )
        restate_person_turn_completed = dispatchers.RestatePersonTurnCompleted(call_orchestrator_workflow)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([call_orchestrator_workflow])),
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
                with pytest.raises(restate.HttpError) as refused:
                    await restate_client.Client(async_client).workflow_call(
                        restate_person_turn_completed.handler, key=f"other-{uuid.uuid4()}", arg=relays.PersonTurnCompletedRequest(call_id="c7", text="Grace")
                    )
                with pytest.raises(restate.HttpError) as early:
                    await restate_client.Client(async_client).workflow_call(
                        restate_person_turn_completed.handler, key=call_id, arg=relays.PersonTurnCompletedRequest(call_id=call_id, text="Grace")
                    )
            promised = await admin.post(
                "/query",
                headers={"accept": "application/json"},
                json={
                    "query": "SELECT key FROM sys_promise "
                    f"WHERE service_name = '{call_orchestrator_workflow.name}' AND service_key = '{call_id}'"
                },
            )

            assert refused.value.status_code == 400
            assert "a message names the call its workflow is keyed by" in (refused.value.body or "")
            assert early.value.status_code == 412
            assert "no call has started under this key" in (early.value.body or "")
            assert promised.json()["rows"] == []
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
