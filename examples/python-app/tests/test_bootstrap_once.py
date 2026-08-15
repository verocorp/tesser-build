from __future__ import annotations

import pytest

import campaign.wiring.wire as campaign_wire
from bootstrap.bootstrap import new
import campaign.application.ports.target_policy as target_policy  # tessercheck:ignore TB070
import campaign.client.client as client
import campaign.wiring.config as config
from tesser.lifecycle import Closeable
from tests.support import app_config


def test_graph_built_once_state_persists_across_calls() -> None:
    app = new(app_config())
    try:
        view = app.campaign.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        app.campaign.add_link(client.AddLinkRequest(view.campaign_id, "a", "https://ok.example/a"))
        app.campaign.add_link(client.AddLinkRequest(view.campaign_id, "b", "https://ok.example/b"))
        assert {v.slug for v in app.campaign.list_links(client.ListLinksRequest()).links} == {"a", "b"}
    finally:
        app.close()


def test_constructor_runs_once_across_many_calls(monkeypatch: pytest.MonkeyPatch) -> None:  # tessercheck:ignore TB030
    calls = {"n": 0}

    original = campaign_wire.build

    def counting(cfg: config.Config, policy: target_policy.TargetPolicy) -> tuple[client.Client, Closeable]:
        calls["n"] += 1
        return original(cfg, policy)

    monkeypatch.setattr(campaign_wire, "build", counting)
    app = new(app_config())
    try:
        for _ in range(5):
            app.campaign.list_links(client.ListLinksRequest())
        assert calls["n"] == 1
    finally:
        app.close()


def test_close_is_idempotent() -> None:
    app = new(app_config())
    app.close()
    app.close()
