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

import alpha.adapters.activities as activities
import alpha.adapters.workflows as workflows
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeWidgetApplicationClient(client.WidgetApplicationClient):

    def __init__(self) -> None:
        self.kept: list[str] = []

    def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self.kept.append(keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestRestateRegisterWidget:

    async def test_register_widget_waits_on_the_promise_the_relays_name_before_it_keeps_anything(self) -> None:
        name = str(uuid.uuid4())
        suffix = uuid.uuid4().hex
        widget_actions_service = restate.Service(f"WidgetActions{suffix}")
        widget_orchestrator_workflow = restate.Workflow(f"WidgetOrchestrator{suffix}")
        fake_widget_application_client = FakeWidgetApplicationClient()
        restate_register_widget = workflows.RestateRegisterWidget(
            widget_orchestrator_workflow,
            activities.RestateKeepWidget(widget_actions_service, fake_widget_application_client),
        )
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([widget_actions_service, widget_orchestrator_workflow])),
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
                    json={"uri": f"http://{os.environ['MINIMAL_CALLBACK_HOST']}:{port}", "force": True},
                )
                if registered.is_success:
                    break
                await asyncio.sleep(0.1)
            assert registered.is_success, registered.text

            async with httpx.AsyncClient(base_url=os.environ["RESTATE_INGRESS"], timeout=30.0) as async_client:
                sent = await restate_client.Client(async_client).workflow_send(
                    restate_register_widget.handler, key=name, arg=relays.RegisterWidgetRequest(name=name)
                )
            awaited: list[str] = []
            for _ in range(100):
                journaled = await admin.post(
                    "/query",
                    headers={"accept": "application/json"},
                    json={
                        "query": "SELECT entry_lite_json FROM sys_journal "
                        f"WHERE id = '{sent.invocation_id}' AND entry_type = 'Command: GetPromise'"
                    },
                )
                awaited = [
                    json.loads(row["entry_lite_json"])["Command"]["GetPromise"]["key"] for row in journaled.json()["rows"]
                ]
                if awaited:
                    break
                await asyncio.sleep(0.05)
            await admin.patch(f"/invocations/{sent.invocation_id}/kill")

            assert awaited == [relays.APPROVE_WIDGET_PROMISE]
            assert fake_widget_application_client.kept == []
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)
