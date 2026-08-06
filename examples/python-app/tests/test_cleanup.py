from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client
import linkpolicy.wiring.wire as linkpolicy_wire
import reports.client
import reports.wiring.wire as reports_wire
from bootstrap.bootstrap import CleanupStack, new
from bootstrap.config import Config
from campaign.wiring.config import Config as CampaignConfig
from errors import DomainError
from lifecycle import Closeable
from linkpolicy.client import (
    CheckRequest,
    CheckResponse,
    Client,
    ListVerdictsRequest,
    ListVerdictsResponse,
)
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.client import LinksByVerdictRequest, LinksByVerdictResponse
from reports.wiring.config import Config as ReportsConfig


@ts.fake
class _Spy(Closeable):
    def __init__(self, name: str, order: list[str], *, fail: bool = False) -> None:
        self.name = name
        self._order = order
        self._fail = fail
        self.closed = False

    def close(self) -> None:
        self.closed = True
        self._order.append(self.name)
        if self._fail:
            raise RuntimeError(f"{self.name} close failed")


def test_stack_closes_reverse_order_and_all_despite_error() -> None:
    order: list[str] = []
    a, b, c = _Spy("a", order), _Spy("b", order, fail=True), _Spy("c", order)
    stack = CleanupStack()
    for r in (a, b, c):
        stack.push(r)
    errors = stack.close_all()
    assert order == ["c", "b", "a"]
    assert a.closed and b.closed and c.closed
    assert len(errors) == 1


@ts.fake
class _DummyPolicy(Client):
    def check(self, req: CheckRequest) -> CheckResponse:
        return CheckResponse(True, "ok")

    def list_verdicts(self, req: ListVerdictsRequest) -> ListVerdictsResponse:
        return ListVerdictsResponse(verdicts=())


def test_new_closes_already_built_deps_on_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore
    order: list[str] = []
    spy = _Spy("linkpolicy", order)

    def fake_build(cfg: LinkPolicyConfig) -> tuple[Client, Closeable]:
        return _DummyPolicy(), spy

    monkeypatch.setattr(linkpolicy_wire, "build", fake_build)

    with pytest.raises(DomainError):
        new(
            Config(
                campaign=CampaignConfig(""),
                linkpolicy=LinkPolicyConfig("memory"),
                reports=ReportsConfig(),
            )
        )
    assert spy.closed, "the already-built linkpolicy resource was not cleaned up"


@ts.fake
class _DummyReports(reports.client.Client):
    def links_by_verdict(self, req: LinksByVerdictRequest) -> LinksByVerdictResponse:
        return LinksByVerdictResponse(links=())


def test_reports_closeable_is_on_the_cleanup_stack(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore
    order: list[str] = []
    spy = _Spy("reports", order)

    def fake_build(
        cfg: ReportsConfig, campaign_client: campaign.client.Client, policy_client: Client
    ) -> tuple[reports.client.Client, Closeable]:
        return _DummyReports(), spy

    monkeypatch.setattr(reports_wire, "build", fake_build)
    app = new(
        Config(
            campaign=CampaignConfig("memory"),
            linkpolicy=LinkPolicyConfig("memory"),
            reports=ReportsConfig(),
        )
    )
    app.close()
    assert spy.closed, "reports' closeable was not on the cleanup stack"


def test_app_close_surfaces_errors_instead_of_dropping(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore
    order: list[str] = []
    failing = _Spy("reports", order, fail=True)

    def fake_build(
        cfg: ReportsConfig, campaign_client: campaign.client.Client, policy_client: Client
    ) -> tuple[reports.client.Client, Closeable]:
        return _DummyReports(), failing

    monkeypatch.setattr(reports_wire, "build", fake_build)
    app = new(
        Config(
            campaign=CampaignConfig("memory"),
            linkpolicy=LinkPolicyConfig("memory"),
            reports=ReportsConfig(),
        )
    )
    app.close()
    assert failing.closed
    assert len(app.close_errors) == 1
