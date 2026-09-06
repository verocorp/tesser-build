from __future__ import annotations

import beta.client as client
import beta.component as component


class TestBetaContext:

    def test_an_unknown_key_is_not_held(self) -> None:
        beta = component.Beta(component.Config(component.Spec(key="k")))
        check_response = beta.client.check(client.CheckRequest(key="x"))
        assert check_response.held == "no"
