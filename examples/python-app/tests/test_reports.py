"""Moment 2 — the cross-context read, demonstrated IN-PROCESS on one App. It reads
both public Clients (campaign links + linkpolicy verdicts) and joins them; the
acyclic decomposition is what lets it exist above both contexts.
"""

from __future__ import annotations

from bootstrap.bootstrap import App, new
from bootstrap.config import Config
from campaign.client import CreateLinkRequest
from campaign.wiring.config import Config as CampaignConfig
from errors import DomainError
from linkpolicy.wiring.config import Config as LinkPolicyConfig


def _mem() -> App:
    return new(Config(campaign=CampaignConfig("memory"), linkpolicy=LinkPolicyConfig("memory")))


def test_report_reads_both_contexts_in_process() -> None:
    app = _mem()
    try:
        app.campaign.create_link(CreateLinkRequest("a", "https://ok.example/a"))
        app.campaign.create_link(CreateLinkRequest("b", "https://ok.example/b"))
        rows = app.reports.links_by_verdict()
        assert {r.slug for r in rows} == {"a", "b"}  # from campaign
        assert all(r.allowed and r.reason == "ok" for r in rows)  # verdict from linkpolicy
    finally:
        app.close()


def test_blocked_destination_never_becomes_a_link() -> None:
    app = _mem()
    try:
        # http scheme is not allowed by linkpolicy -> create fails closed, no link
        try:
            app.campaign.create_link(CreateLinkRequest("bad", "http://ok.example/a"))
        except DomainError:
            pass
        assert app.reports.links_by_verdict() == ()
    finally:
        app.close()
