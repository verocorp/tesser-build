from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports as ports
import alpha.client as client
import alpha.component.component as component
import alpha.component.config as config


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.OK)


class TestAlpha:

    def test_the_wired_client_adds_a_widget(self) -> None:
        alpha = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaCheck())
        added = alpha.client.add(client.AddRequest(name="a", part="p"))
        assert added.name == "a"
