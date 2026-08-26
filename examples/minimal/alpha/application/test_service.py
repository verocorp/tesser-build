from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.thing_repository as thing_repository
import alpha.application.service as service
import alpha.client.client as client


@ts.fake
class FakeThingRepository(thing_repository.ThingRepository):

    def save(self, request: thing_repository.SaveRequest) -> thing_repository.SaveResponse:
        return thing_repository.SaveResponse(name=request.name)


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


@ts.helper
def add_request(name: str = "a") -> client.AddRequest:
    return client.AddRequest(name=name)


def test_add_answers_the_added_name() -> None:
    assert service.AlphaService(FakeThingRepository(), FakeBetaCheck()).add(add_request()).name == "a"
