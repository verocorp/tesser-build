from __future__ import annotations

import beta.client.client as client
import beta.component.component as component
import beta.component.config as config


def test_an_unknown_key_is_not_held() -> None:
    wired = component.Beta(config.Config(config.Spec(keys=())))
    assert wired.client.check(client.CheckRequest(key="k")).held == "no"
