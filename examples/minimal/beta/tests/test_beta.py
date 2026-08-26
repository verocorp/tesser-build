from __future__ import annotations

import beta.client.client as client
import beta.component.component as component
import beta.component.config as config


class TestBetaContext:

    def test_an_unknown_key_is_not_held(self) -> None:
        wired = component.Beta(config.Config(config.Spec(key="k")))
        checked = wired.client.check(client.CheckRequest(key="x"))
        assert checked.held == "no"
