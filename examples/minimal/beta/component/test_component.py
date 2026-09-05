from __future__ import annotations

import beta.client as client
import beta.component.component as component
import beta.component.config as config


class TestBeta:

    def test_the_wired_client_checks_the_configured_key(self) -> None:
        beta = component.Beta(config.Config(config.Spec(key="k")))
        checked = beta.client.check(client.CheckRequest(key="k"))
        assert checked.held == "yes"
