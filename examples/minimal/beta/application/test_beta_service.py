from __future__ import annotations

import tesser.testing as ts

import beta.application.beta_service as beta_service
import beta.application.ports as ports
import beta.client as client


@ts.fake
class FakeKeyRepository(ports.KeyRepository):

    def has(self, has_key_request: ports.HasKeyRequest) -> ports.HasKeyResponse:
        return ports.HasKeyResponse(held=ports.Held.YES)


class TestBetaService:

    def test_check_reports_what_the_repository_holds(self) -> None:
        application_beta_service = beta_service.BetaService(FakeKeyRepository())
        checked = application_beta_service.check(client.CheckRequest(key="k"))
        assert checked.held == "yes"
