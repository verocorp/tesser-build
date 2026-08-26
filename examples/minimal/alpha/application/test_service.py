from __future__ import annotations

import pytest
import tesser.testing as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.whole_repository as whole_repository
import alpha.application.service as service
import alpha.client.client as client
import tesser.errors as errors


@ts.fake
class FakeWholeRepository(whole_repository.WholeRepository):

    def __init__(self) -> None:
        self.rows: dict[str, whole_repository.WholeRecord] = {}

    def save(self, request: whole_repository.SaveWholeRequest) -> whole_repository.SaveWholeResponse:
        self.rows[request.id] = whole_repository.WholeRecord(request.id, request.name, request.count)
        return whole_repository.SaveWholeResponse()

    def find(self, request: whole_repository.FindWholeRequest) -> whole_repository.FindWholeResponse:
        row = self.rows.get(request.id)
        if row is None:
            return whole_repository.FindWholeResponse(whole_repository.Lookup.ABSENT, ())
        return whole_repository.FindWholeResponse(whole_repository.Lookup.PRESENT, (row,))


@ts.fake
class FakeBetaCheck(beta_check.BetaCheck):

    def __init__(self, verdict: beta_check.Verdict) -> None:
        self.verdict = verdict

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        return beta_check.CheckResponse(verdict=self.verdict)


@ts.helper
def add_request(id: str = "w", name: str = "a", count: int = 1) -> client.AddRequest:
    return client.AddRequest(id=id, name=name, count=count)


def test_add_then_get_serves_the_whole() -> None:
    svc = service.AlphaService(FakeWholeRepository(), FakeBetaCheck(beta_check.Verdict.OK))
    added = svc.add(add_request())
    got = svc.get(client.GetRequest(id="w"))
    assert tuple(view.id for view in added.wholes) == ("w",)
    assert tuple(view.id for view in got.wholes) == ("w",)


def test_get_of_an_unknown_whole_answers_empty() -> None:
    svc = service.AlphaService(FakeWholeRepository(), FakeBetaCheck(beta_check.Verdict.OK))
    assert svc.get(client.GetRequest(id="nope")).wholes == ()


def test_get_of_a_malformed_id_is_a_domain_error() -> None:
    svc = service.AlphaService(FakeWholeRepository(), FakeBetaCheck(beta_check.Verdict.OK))
    with pytest.raises(errors.DomainError):
        svc.get(client.GetRequest(id="A1"))


class TestRefusal:

    def test_a_refused_check_adds_no_view(self) -> None:
        svc = service.AlphaService(FakeWholeRepository(), FakeBetaCheck(beta_check.Verdict.REFUSED))
        assert svc.add(add_request()).wholes == ()
