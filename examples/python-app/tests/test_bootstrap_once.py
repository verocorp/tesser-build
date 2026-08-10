from __future__ import annotations

import pytest

import campaign.wiring.wire as campaign_wire
from bootstrap.bootstrap import new
from campaign.application.service import TargetPolicy
from campaign.client.client import AddLinkRequest, Client, CreateCampaignRequest, ListLinksRequest
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as real_campaign_build
from lifecycle import Closeable
from tests.support import app_config


def test_graph_built_once_state_persists_across_calls() -> None:
    app = new(app_config())
    try:
        view = app.campaign.create_campaign(CreateCampaignRequest("100.00", "USD"))
        app.campaign.add_link(AddLinkRequest(view.campaign_id, "a", "https://ok.example/a"))
        app.campaign.add_link(AddLinkRequest(view.campaign_id, "b", "https://ok.example/b"))
        assert {v.slug for v in app.campaign.list_links(ListLinksRequest()).links} == {"a", "b"}
    finally:
        app.close()


def test_constructor_runs_once_across_many_calls(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore
    calls = {"n": 0}

    def counting(cfg: CampaignConfig, policy: TargetPolicy) -> tuple[Client, Closeable]:
        calls["n"] += 1
        return real_campaign_build(cfg, policy)

    monkeypatch.setattr(campaign_wire, "build", counting)
    app = new(app_config())
    try:
        for _ in range(5):
            app.campaign.list_links(ListLinksRequest())
        assert calls["n"] == 1
    finally:
        app.close()


def test_close_is_idempotent() -> None:
    app = new(app_config())
    app.close()
    app.close()
