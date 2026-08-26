from __future__ import annotations

import tesser.testing as ts

import beta.application.beta_service as beta_service
import beta.application.ports.key_store as key_store
import beta.client.client as client


@ts.fake
class FakeKeyStore(key_store.KeyStore):

    def has(self, request: key_store.HasKeyRequest) -> key_store.HasKeyResponse:
        return key_store.HasKeyResponse(held=key_store.Held.YES)


class TestBetaService:

    def test_check_reports_what_the_store_holds(self) -> None:
        service = beta_service.BetaService(FakeKeyStore())
        checked = service.check(client.CheckRequest(key="k"))
        assert checked.held == "yes"
