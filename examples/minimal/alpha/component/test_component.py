from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlpha:

    def test_the_wired_client_adds_a_widget(self) -> None:
        wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaCheck())
        added = wired.client.add(client.AddRequest(name="a"))
        assert added.name == "a"
