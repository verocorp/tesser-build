from __future__ import annotations

from bootstrap.bootstrap import App, new
from bootstrap.config import Config
from campaign.client import CreateLinkRequest
from campaign.wiring.config import Config as CampaignConfig
from errors import DomainError
from linkpolicy.wiring.config import Config as LinkPolicyConfig
from reports.domain.report import Link, RecordedVerdict, join_links_with_verdicts
from reports.wiring.config import Config as ReportsConfig


def _mem() -> App:
    return new(
        Config(
            campaign=CampaignConfig("memory"),
            linkpolicy=LinkPolicyConfig("memory"),
            reports=ReportsConfig(),
        )
    )


def test_report_reads_both_contexts_in_process() -> None:
    app = _mem()
    try:
        app.campaign.create_link(CreateLinkRequest("a", "https://ok.example/a"))
        app.campaign.create_link(CreateLinkRequest("b", "https://ok.example/b"))
        rows = app.reports.links_by_verdict()
        assert {r.slug for r in rows} == {"a", "b"}
        assert all(r.allowed and r.reason == "ok" for r in rows)
    finally:
        app.close()


def test_blocked_destination_never_becomes_a_link() -> None:
    app = _mem()
    try:
        try:
            app.campaign.create_link(CreateLinkRequest("bad", "http://ok.example/a"))
        except DomainError:
            pass
        assert app.reports.links_by_verdict() == ()
    finally:
        app.close()


def test_join_semantics_default_and_ordering() -> None:
    links = (Link("z", "https://ok.example/z"), Link("a", "https://bad.example/a"))
    verdicts = (RecordedVerdict("https://bad.example/a", False, "host blocked"),)
    rows = join_links_with_verdicts(links, verdicts)
    assert [r.slug for r in rows] == ["a", "z"]
    assert not rows[0].allowed and rows[0].reason == "host blocked"
    assert rows[1].allowed and rows[1].reason == "no verdict recorded"
