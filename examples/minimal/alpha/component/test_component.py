from __future__ import annotations

import os

import tesser.testing as ts

import alpha.application.ports as ports
import alpha.client as client
import alpha.component as component


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.OK)


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(storage="postgres://a@b/c", ingress="http://localhost:8080")
        config = component.Config(spec)
        assert config.storage == spec.storage


class TestAlpha:

    async def test_the_wired_client_adds_a_widget(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage=os.environ["ALPHA_STORAGE"], ingress="http://localhost:8080")), FakeBetaCheck())
        add_part_response = await alpha.client.add_part(client.AddPartRequest(name="a", part="p"))
        assert add_part_response.name == "a"

    def test_only_the_workflow_faces_the_ingress_and_each_container_holds_its_handlers(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage="postgres://a@b/c", ingress="http://localhost:8080")), FakeBetaCheck())
        declared = [
            (registered.name, registered.ingress_private, sorted(registered.handlers))
            for registered in (alpha.widget_actions_service, alpha.widget_orchestrator_workflow)
        ]
        assert declared == [
            ("WidgetActions", True, ["keep_widget"]),
            ("WidgetOrchestrator", None, ["approve_widget", "register_widget"]),
        ]
