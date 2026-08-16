from __future__ import annotations

import pytest
import tesser.testing as ts

from bootstrap.bootstrap import App, CleanupStack, new
from bootstrap.config import Config
import campaign.client.client as campaign_client
import campaign.wiring.config as campaign_config
from tesser.errors import DomainError
from tesser.lifecycle import Closeable
import linkpolicy.wiring.config as linkpolicy_config
import reports.client.client as reports_client
import reports.wiring.config as reports_config


@ts.fake
class FakeCloseableSpy(Closeable):
    def __init__(self, name: str, order: list[str], *, fail: bool = False) -> None:
        self.name = name
        self.closes = 0
        self._order = order
        self._fail = fail

    def close(self) -> None:
        self.closes += 1
        self._order.append(self.name)
        if self._fail:
            raise RuntimeError(f"{self.name} refused to close")


def test_the_stack_closes_in_reverse_order() -> None:
    order: list[str] = []
    stack = CleanupStack()
    for name in ("first", "second", "third"):
        stack.push(FakeCloseableSpy(name, order))
    assert stack.close_all() == []
    assert order == ["third", "second", "first"]


def test_the_stack_closes_every_resource_despite_an_error() -> None:
    order: list[str] = []
    first = FakeCloseableSpy("first", order)
    middle = FakeCloseableSpy("middle", order, fail=True)
    last = FakeCloseableSpy("last", order)
    stack = CleanupStack()
    for resource in (first, middle, last):
        stack.push(resource)
    errors = stack.close_all()
    assert order == ["last", "middle", "first"]
    assert (first.closes, middle.closes, last.closes) == (1, 1, 1)
    assert len(errors) == 1
    assert "middle refused to close" in str(errors[0])


def test_a_drained_stack_closes_nothing_a_second_time() -> None:
    order: list[str] = []
    resource = FakeCloseableSpy("only", order)
    stack = CleanupStack()
    stack.push(resource)
    stack.close_all()
    assert stack.close_all() == []
    assert resource.closes == 1


def test_an_empty_stack_reports_no_errors() -> None:
    assert CleanupStack().close_all() == []


def test_the_composed_app_serves_a_campaign_across_its_contexts() -> None:
    app = new(
        Config(
            campaign=campaign_config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    try:
        view = app.campaign.create_campaign(campaign_client.CreateCampaignRequest("100.00", "USD"))
        app.campaign.add_link(
            campaign_client.AddLinkRequest(view.campaign_id, "summer", "https://ok.example/a")
        )
        rows = app.reports.links_by_verdict(reports_client.LinksByVerdictRequest()).links
        assert [(row.slug, row.allowed, row.reason) for row in rows] == [("summer", True, "ok")]
    finally:
        app.close()


def test_the_composed_app_carries_the_policy_the_wiring_gave_it() -> None:
    app = new(
        Config(
            campaign=campaign_config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    try:
        view = app.campaign.create_campaign(campaign_client.CreateCampaignRequest("100.00", "USD"))
        with pytest.raises(DomainError):
            app.campaign.add_link(
                campaign_client.AddLinkRequest(view.campaign_id, "plain", "http://ok.example/a")
            )
        assert app.reports.links_by_verdict(reports_client.LinksByVerdictRequest()).links == ()
    finally:
        app.close()


def test_an_unbuildable_dependency_fails_the_whole_composition() -> None:
    with pytest.raises(DomainError) as caught:
        new(
            Config(
                campaign=campaign_config.Config(""),
                linkpolicy=linkpolicy_config.Config("memory"),
                reports=reports_config.Config(),
            )
        )
    assert caught.value.code == "missing_coordinate"


def test_closing_the_app_twice_closes_its_resources_once() -> None:
    order: list[str] = []
    resource = FakeCloseableSpy("gateway", order)
    stack = CleanupStack()
    stack.push(resource)
    built = new(
        Config(
            campaign=campaign_config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    try:
        app = App(built.campaign, built.linkpolicy, built.reports, stack)
        app.close()
        app.close()
        assert resource.closes == 1
        assert app.close_errors == ()
    finally:
        built.close()


def test_a_refused_close_is_surfaced_instead_of_raised() -> None:
    order: list[str] = []
    resource = FakeCloseableSpy("gateway", order, fail=True)
    stack = CleanupStack()
    stack.push(resource)
    built = new(
        Config(
            campaign=campaign_config.Config("memory"),
            linkpolicy=linkpolicy_config.Config("memory"),
            reports=reports_config.Config(),
        )
    )
    try:
        app = App(built.campaign, built.linkpolicy, built.reports, stack)
        app.close()
        assert resource.closes == 1
        assert len(app.close_errors) == 1
        assert "gateway refused to close" in str(app.close_errors[0])
    finally:
        built.close()
