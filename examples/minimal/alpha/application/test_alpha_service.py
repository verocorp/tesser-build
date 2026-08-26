from __future__ import annotations

import tesser.testing as ts

import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client


@ts.fake
class FakeWidgetRepository(widget_repository.WidgetRepository):

    def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        return widget_repository.SaveResponse(name=request.name)


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


@ts.helper
def add_request(name: str = "a") -> client.AddRequest:
    return client.AddRequest(name=name)


class TestAlphaService:

    def test_add_answers_the_added_name(self) -> None:
        service = alpha_service.AlphaService(FakeWidgetRepository(), FakeBetaCheck())
        added = service.add(add_request())
        assert added.name == "a"
