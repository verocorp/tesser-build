from __future__ import annotations

import beta.client.client as client
import beta.component.component as component
import beta.component.config as config


def test_the_wired_client_checks_the_configured_key() -> None:
    wired = component.Beta(config.Config(config.Spec(key="k")))
    assert wired.client.check(client.CheckRequest(key="k")).held == "yes"
    wired.close()
