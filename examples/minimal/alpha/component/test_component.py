from __future__ import annotations

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
        spec = component.Spec(storage="memory")
        config = component.Config(spec)
        assert config.storage == spec.storage


class TestAlpha:

    def test_the_wired_client_adds_a_widget(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage="memory")), FakeBetaCheck())
        add_part_response = alpha.client.add_part(client.AddPartRequest(name="a", part="p"))
        assert add_part_response.name == "a"

    def test_the_wired_client_creates_a_widget(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage="memory")), FakeBetaCheck())
        create_widget_response = alpha.client.create_widget(client.CreateWidgetRequest(name="a"))
        assert create_widget_response.name == "a"
