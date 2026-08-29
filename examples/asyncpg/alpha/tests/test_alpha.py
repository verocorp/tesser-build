from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.application.ports.beta_check as beta_check
import alpha.component.component as component
import alpha.component.config as config
import protocol.cli as protocol_cli


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlphaContext:

    async def test_a_cli_add_reaches_the_wired_service(self) -> None:
        wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaCheck())
        response = await cli.Handler(wired.client).add(protocol_cli.CliRequest(args=("a", "p")))
        await wired.close()
        assert response.line.text == "a"
