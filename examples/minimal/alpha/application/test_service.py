from __future__ import annotations

import pytest
import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.thing_repository as thing_repository
import alpha.application.service as service
import alpha.client.client as client
import tesser.errors as errors


@ts.fake
class FakeThingRepository(thing_repository.ThingRepository):

    def save(self, request: thing_repository.SaveRequest) -> thing_repository.SaveResponse:
        return thing_repository.SaveResponse()


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=beta_check.Verdict.OK)


@ts.helper
def add_request(name: str = "a") -> client.AddRequest:
    return client.AddRequest(name=name)


def test_add_answers_the_added_name() -> None:
    svc = service.AlphaService(FakeThingRepository(), FakeBetaCheck())
    assert svc.add(add_request()).name == "a"


class TestRejection:

    def test_an_empty_name_is_a_domain_error(self) -> None:
        svc = service.AlphaService(FakeThingRepository(), FakeBetaCheck())
        with pytest.raises(errors.DomainError):
            svc.add(add_request(name=""))
