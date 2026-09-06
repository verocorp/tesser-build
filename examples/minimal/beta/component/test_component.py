from __future__ import annotations

import beta.client as client
import beta.component as component


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = component.Spec(key="k")
        config = component.Config(spec)
        assert config.key == spec.key


class TestBeta:

    def test_the_wired_client_checks_the_configured_key(self) -> None:
        beta = component.Beta(component.Config(component.Spec(key="k")))
        check_response = beta.client.check(client.CheckRequest(key="k"))
        assert check_response.held == "yes"
