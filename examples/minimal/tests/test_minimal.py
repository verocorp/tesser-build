from __future__ import annotations

import asyncio
import os
import uuid

import alpha.client as alpha_client
import alpha.component as alpha_component
import app
import beta.component as beta_component


class TestWiredApp:

    def test_a_real_alpha_reaches_a_real_beta(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory", "http://localhost:8080")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        assert minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="a", part="p")).name == "a"

    def test_a_widget_beta_holds_a_key_for_stands_as_kept(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory", "http://localhost:8080")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        add_part_response = minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="k", part="k"))
        assert add_part_response.standing == "kept"

    def test_a_widget_beta_holds_no_key_for_stands_as_released(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory", "http://localhost:8080")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        add_part_response = minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="z", part="z"))
        assert add_part_response.standing == "released"

    async def test_creating_a_widget_waits_in_the_engine_until_its_name_is_approved(self) -> None:
        name = "w-" + str(uuid.uuid4())
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec("memory", os.environ["RESTATE_INGRESS"])),
            beta_component.Config(beta_component.Spec("a")),
        )
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        creating = asyncio.create_task(minimal_app.alpha.client.create_widget(alpha_client.CreateWidgetRequest(name=name)))
        await asyncio.sleep(0.5)
        waited = not creating.done()
        await minimal_app.alpha.client.approve_widget(alpha_client.ApproveWidgetRequest(name=name))
        create_widget_response = await creating
        assert waited
        assert create_widget_response.name == name
