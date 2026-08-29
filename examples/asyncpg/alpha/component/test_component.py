from __future__ import annotations

import pytest

import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config
import tesser.errors as errors


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    async def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


class TestAlpha:

    async def test_the_memory_coordinate_wires_a_client_that_adds_a_widget(self) -> None:
        wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaCheck())
        added = await wired.client.add(client.AddRequest(name="a", part="p"))
        await wired.close()
        assert added.name == "a"

    async def test_a_postgres_coordinate_wires_without_connecting(self) -> None:
        wired = component.Alpha(config.Config(config.Spec(storage="postgres://nobody@nowhere/none")), FakeBetaCheck())
        await wired.close()

    def test_an_unknown_coordinate_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            component.Alpha(config.Config(config.Spec(storage="")), FakeBetaCheck())
        assert caught.value.code == "unknown_backend"
