from __future__ import annotations

import asyncio
import os
import uuid

import alpha.client as alpha_client
import alpha.component as alpha_component
import app
import beta.component as beta_component


class TestWiredApp:

    async def test_a_widget_beta_holds_a_key_for_stands_as_kept_and_one_it_holds_none_for_as_released(self) -> None:
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec(os.environ["ALPHA_STORAGE"], os.environ["RESTATE_INGRESS"])),
            beta_component.Config(beta_component.Spec("a")),
        )
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        kept = await minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="k", part="k"))
        released = await minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="z", part="z"))
        assert (kept.standing, released.standing) == ("kept", "released")

    async def test_a_created_widget_is_found_once_its_name_is_approved(self) -> None:
        name = "w-" + str(uuid.uuid4())
        spec = app.Spec(
            alpha_component.Config(alpha_component.Spec(os.environ["ALPHA_STORAGE"], os.environ["RESTATE_INGRESS"])),
            beta_component.Config(beta_component.Spec("a")),
        )
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        create_widget_response = await minimal_app.alpha.client.create_widget(alpha_client.CreateWidgetRequest(name=name))
        found_before_approval = await minimal_app.alpha.client.find_widget(alpha_client.FindWidgetRequest(name=name))
        await minimal_app.alpha.client.approve_widget(alpha_client.ApproveWidgetRequest(name=name))
        found = found_before_approval
        for _ in range(100):
            found = await minimal_app.alpha.client.find_widget(alpha_client.FindWidgetRequest(name=name))
            if found.found == "yes":
                break
            await asyncio.sleep(0.05)
        assert create_widget_response.name == name
        assert (found_before_approval.found, found.found) == ("no", "yes")
