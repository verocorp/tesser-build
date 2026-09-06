from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.application.ports as ports
import alpha.component as component
import protocol.cli as cli


@ts.fake
class FakeBetaCheck(ports.BetaCheck):

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        return ports.CheckResponse(verdict=ports.Verdict.OK)


class TestAlphaContext:

    def test_a_cli_add_reaches_the_wired_service(self) -> None:
        alpha = component.Alpha(component.Config(component.Spec(storage="memory")), FakeBetaCheck())
        response = handlers.Handler(alpha.client).add(cli.CliRequest(args=("a", "p")))
        assert response.line.text == "a"
