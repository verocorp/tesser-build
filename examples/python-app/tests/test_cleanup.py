from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.client.client as campaign_client
import linkpolicy.wiring.wire as linkpolicy_wire
import reports.client.client as reports_client
import reports.wiring.wire as reports_wire
from bootstrap.bootstrap import CleanupStack, new
from bootstrap.config import Config
import campaign.wiring.config as config
from tesser.errors import DomainError
from tesser.lifecycle import Closeable
import linkpolicy.client.client as client
import linkpolicy.wiring.config as linkpolicy_config
import reports.client.client as reports_client2
import reports.wiring.config as reports_config


@ts.fake
class FakeCloseableSpy(Closeable):
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
    a, b, c = FakeCloseableSpy("a", order), FakeCloseableSpy("b", order, fail=True), FakeCloseableSpy("c", order)
    stack = CleanupStack()
    for r in (a, b, c):
        stack.push(r)
    errors = stack.close_all()
    assert order == ["c", "b", "a"]
    assert a.closed and b.closed and c.closed
    assert len(errors) == 1


@ts.fake
class FakeLinkPolicyClientAllowAll(client.Client):
    def check(self, req: client.CheckRequest) -> client.CheckResponse:
        return client.CheckResponse(True, "ok")

    def list_verdicts(self, req: client.ListVerdictsRequest) -> client.ListVerdictsResponse:
        return client.ListVerdictsResponse(verdicts=())


def test_new_closes_already_built_deps_on_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore TB030
    order: list[str] = []
    spy = FakeCloseableSpy("linkpolicy", order)

    def fake_build(cfg: linkpolicy_config.Config) -> tuple[client.Client, Closeable]:
        return FakeLinkPolicyClientAllowAll(), spy

    monkeypatch.setattr(linkpolicy_wire, "build", fake_build)

    with pytest.raises(DomainError):
        new(
            Config(
                campaign=config.Config(""),
                linkpolicy=linkpolicy_config.Config("memory"),
                reports=reports_config.Config(),
            )
        )
    assert spy.closed, "the already-built linkpolicy resource was not cleaned up"


@ts.fake
class FakeReportsClientEmpty(reports_client.Client):
    def links_by_verdict(self, req: reports_client2.LinksByVerdictRequest) -> reports_client2.LinksByVerdictResponse:
        return reports_client2.LinksByVerdictResponse(links=())


def test_reports_closeable_is_on_the_cleanup_stack(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore TB030
    order: list[str] = []
    spy = FakeCloseableSpy("reports", order)

    def fake_build(
        cfg: reports_config.Config, campaign_client: campaign_client.Client, policy_client: client.Client
    ) -> tuple[reports_client.Client, Closeable]:
        return FakeReportsClientEmpty(), spy

    monkeypatch.setattr(reports_wire, "build", fake_build)
    app = new(
        Config(
            campaign=config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    app.close()
    assert spy.closed, "reports' closeable was not on the cleanup stack"


def test_app_close_surfaces_errors_instead_of_dropping(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore TB030
    order: list[str] = []
    failing = FakeCloseableSpy("reports", order, fail=True)

    def fake_build(
        cfg: reports_config.Config, campaign_client: campaign_client.Client, policy_client: client.Client
    ) -> tuple[reports_client.Client, Closeable]:
        return FakeReportsClientEmpty(), failing

    monkeypatch.setattr(reports_wire, "build", fake_build)
    app = new(
        Config(
            campaign=config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    app.close()
    assert failing.closed
    assert len(app.close_errors) == 1
