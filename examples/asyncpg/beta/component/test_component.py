from __future__ import annotations

import pytest

import beta.client.client as client
import beta.component.component as component
import beta.component.config as config
import tesser.errors as errors


class TestBeta:

    async def test_the_memory_coordinate_wires_a_client_that_holds_and_checks(self) -> None:
        wired = component.Beta(config.Config(config.Spec(storage="memory")))
        await wired.client.hold(client.HoldRequest(key="k"))
        checked = await wired.client.check(client.CheckRequest(key="k"))
        await wired.close()
        assert checked.held == "yes"

    async def test_a_postgres_coordinate_wires_without_connecting(self) -> None:
        wired = component.Beta(config.Config(config.Spec(storage="postgresql://nobody@nowhere/none")))
        await wired.close()

    def test_an_unknown_coordinate_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            component.Beta(config.Config(config.Spec(storage="sqlite")))
        assert caught.value.code == "unknown_backend"
