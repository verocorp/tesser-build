from __future__ import annotations

import beta.client as client
import beta.component as component


class TestBetaContext:

    def test_an_unknown_key_is_not_held(self) -> None:
        beta = component.Beta(component.Config(component.Spec(key="k")))
        check_key_response = beta.client.check_key(client.CheckKeyRequest(key="x"))
        assert check_key_response.held == "no"
