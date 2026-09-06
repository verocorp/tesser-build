from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.application.ports as ports
import alpha.component as component
import protocol


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.OK)


class TestAlphaContext:

    def test_a_cli_add_reaches_the_wired_service(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage="memory")), FakeBetaCheck())
        cli_response = handlers.Handler(alpha.client).add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.line.text == "a"
