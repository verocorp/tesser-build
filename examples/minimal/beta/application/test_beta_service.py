from __future__ import annotations

import tesser.testing as ts

import beta.application.beta_service as beta_service
import beta.application.ports.key_repository as key_repository
import beta.client.client as client


@ts.fake
class FakeKeyRepository(key_repository.KeyRepository):

    def has(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        return key_repository.HasKeyResponse(held=key_repository.Held.YES)


class TestBetaService:

    def test_check_reports_what_the_repository_holds(self) -> None:
        service = beta_service.BetaService(FakeKeyRepository())
        checked = service.check(client.CheckRequest(key="k"))
        assert checked.held == "yes"
