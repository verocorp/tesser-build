"""Built-once-per-process + idempotent Close. The graph is constructed exactly once
via ``bootstrap.new``; many client calls reuse it (state persists across calls), and
``close()`` is safe to call twice.
"""

from __future__ import annotations

import pytest

import campaign.wiring.wire as campaign_wire
from bootstrap.bootstrap import App, new
from bootstrap.config import Config
from campaign.client import Client, CreateLinkRequest, TargetChecker
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as real_campaign_build
from lifecycle import Closeable
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.wiring.config import Config as ReportsConfig


def _mem() -> App:
    return new(
        Config(
            campaign=CampaignConfig("memory"),
            linkpolicy=LinkPolicyConfig("memory"),
            reports=ReportsConfig(),
        )
    )


def test_graph_built_once_state_persists_across_calls() -> None:
    app = _mem()
    try:
        app.campaign.create_link(CreateLinkRequest("a", "https://ok.example/a"))
        app.campaign.create_link(CreateLinkRequest("b", "https://ok.example/b"))
        # Both persisted in the SAME repo — the graph is not rebuilt per call.
        assert {v.slug for v in app.campaign.list_links()} == {"a", "b"}
    finally:
        app.close()


def test_constructor_runs_once_across_many_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting(cfg: CampaignConfig, checker: TargetChecker) -> tuple[Client, Closeable]:
        calls["n"] += 1
        return real_campaign_build(cfg, checker)

    monkeypatch.setattr(campaign_wire, "build", counting)
    app = _mem()
    try:
        for _ in range(5):
            app.campaign.list_links()
        assert calls["n"] == 1  # one construction, reused across calls
    finally:
        app.close()


def test_close_is_idempotent() -> None:
    app = _mem()
    app.close()
    app.close()  # no error on a second close
