from __future__ import annotations

from bootstrap.bootstrap import new
import campaign.client.client as client
from errors import DomainError
import reports.client.client as reports_client
import reports.domain.report as report
from tests.support import app_config


def test_report_reads_both_contexts_in_process() -> None:
    app = new(app_config())
    try:
        view = app.campaign.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        app.campaign.add_link(client.AddLinkRequest(view.campaign_id, "a", "https://ok.example/a"))
        app.campaign.add_link(client.AddLinkRequest(view.campaign_id, "b", "https://ok.example/b"))
        rows = app.reports.links_by_verdict(reports_client.LinksByVerdictRequest()).links
        assert {r.slug for r in rows} == {"a", "b"}
        assert all(r.allowed and r.reason == "ok" for r in rows)
    finally:
        app.close()


def test_blocked_destination_never_becomes_a_link() -> None:
    app = new(app_config())
    try:
        view = app.campaign.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        try:
            app.campaign.add_link(client.AddLinkRequest(view.campaign_id, "bad", "http://ok.example/a"))
        except DomainError:
            pass
        assert app.reports.links_by_verdict(reports_client.LinksByVerdictRequest()).links == ()
    finally:
        app.close()


def test_join_semantics_default_and_ordering() -> None:
    links = (report.Link("z", "https://ok.example/z"), report.Link("a", "https://bad.example/a"))
    verdicts = (report.RecordedVerdict("https://bad.example/a", False, "host blocked"),)
    rows = report.join_links_with_verdicts(links, verdicts)
    assert [str(r.slug) for r in rows] == ["a", "z"]
    assert str(rows[0].allowed) == "denied" and str(rows[0].reason) == "host blocked"
    assert str(rows[1].allowed) == "allowed" and str(rows[1].reason) == "no verdict recorded"
