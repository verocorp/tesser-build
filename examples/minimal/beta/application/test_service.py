from __future__ import annotations

import tesser.testing as ts

import beta.application.ports.key_store as key_store
import beta.application.service as service
import beta.client.client as client


@ts.fake
class FakeKeyStore(key_store.KeyStore):

    def __init__(self, held: key_store.Held) -> None:
        self.held = held

    def has(self, request: key_store.HasKeyRequest) -> key_store.HasKeyResponse:
        return key_store.HasKeyResponse(held=self.held)


def test_check_reports_what_the_store_holds() -> None:
    svc = service.BetaService(FakeKeyStore(key_store.Held.YES))
    assert svc.check(client.CheckRequest(key="k")).held == "yes"
