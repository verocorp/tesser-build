from __future__ import annotations

import tesser.testing as ts

import beta.application as application
import beta.application.ports as ports
import beta.client as client


@ts.fake
class FakeKeyRepository(ports.KeyRepository):

    def has(self, has_key_request: ports.HasKeyRequest) -> ports.HasKeyResponse:
        return ports.HasKeyResponse(held=ports.Held.YES)


class TestBetaService:

    def test_check_reports_what_the_repository_holds(self) -> None:
        beta_service = application.BetaService(FakeKeyRepository())
        check_response = beta_service.check(client.CheckRequest(key="k"))
        assert check_response.held == "yes"
