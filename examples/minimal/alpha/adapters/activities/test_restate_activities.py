from __future__ import annotations

import asyncio
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
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeWidgetApplicationClient(client.WidgetApplicationClient):

    def __init__(self) -> None:
        self.kept: list[str] = []

    def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self.kept.append(keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestRestateKeepWidget:

    async def test_restate_serves_keep_widget_and_a_call_made_with_its_handler_reaches_the_application_client(self) -> None:
        widget_actions_service = restate.Service(f"WidgetActions{uuid.uuid4().hex}")
        fake_widget_application_client = FakeWidgetApplicationClient()
        restate_keep_widget = activities.RestateKeepWidget(widget_actions_service, fake_widget_application_client)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([widget_actions_service])),
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
                keep_widget_response = await restate_client.Client(async_client).service_call(
                    restate_keep_widget.handler, relays.KeepWidgetRequest(name="a")
                )

            assert keep_widget_response == relays.KeepWidgetResponse(name="a")
            assert fake_widget_application_client.kept == ["a"]
        finally:
            if registered.is_success:
                await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
            await admin.aclose()
            shutdown.set()
            await asyncio.wait([serving], timeout=1.0)
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)
