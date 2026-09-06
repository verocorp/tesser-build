from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports as ports
import alpha.client as client
import alpha.component as component


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.OK)


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(storage="memory")
        config = component.Config(spec)
        assert config.storage == spec.storage


class TestAlpha:

    def test_the_wired_client_adds_a_widget(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage="memory")), FakeBetaCheck())
        add_response = alpha.client.add(client.AddRequest(name="a", part="p"))
        assert add_response.name == "a"
