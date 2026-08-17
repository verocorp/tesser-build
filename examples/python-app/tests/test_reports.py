from __future__ import annotations

import app.app as app
import campaign.client.client as client
import reports.client.client as reports_client
from tesser.errors import DomainError
from tests.support import app_config


def test_report_reads_both_components_in_process() -> None:
    built = app.App(app_config())
    try:
        view = built.campaign.client.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        built.campaign.client.add_link(
            client.AddLinkRequest(view.campaign_id, "a", "https://ok.example/a")
        )
        built.campaign.client.add_link(
            client.AddLinkRequest(view.campaign_id, "b", "https://ok.example/b")
        )
        rows = built.reports.client.links_by_verdict(reports_client.LinksByVerdictRequest()).links
        assert {r.slug for r in rows} == {"a", "b"}
        assert all(r.allowed and r.reason == "ok" for r in rows)
    finally:
        built.close()


def test_blocked_destination_never_becomes_a_link() -> None:
    built = app.App(app_config())
    try:
        view = built.campaign.client.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        try:
            built.campaign.client.add_link(
                client.AddLinkRequest(view.campaign_id, "bad", "http://ok.example/a")
            )
        except DomainError:
            pass
        assert (
            built.reports.client.links_by_verdict(reports_client.LinksByVerdictRequest()).links
            == ()
        )
    finally:
        built.close()
