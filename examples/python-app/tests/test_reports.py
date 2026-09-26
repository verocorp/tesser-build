from __future__ import annotations

import app as app
import campaign.client as campaign_client
import reports.client as reports_client

import campaign.component as campaign_component
import linkpolicy.component as linkpolicy_component
import reports.component as reports_component


def test_report_reads_both_components_in_process() -> None:
    python_app = app.PythonApp(
        app.AppConfig(
            app.Spec(
                campaign=campaign_component.Config(campaign_component.Spec("memory")),
                linkpolicy=linkpolicy_component.Config(
                    linkpolicy_component.Spec("memory")
                ),
                reports=reports_component.Config(reports_component.Spec()),
                http=app.HttpConfig(app.HttpSpec("", 8080)),
            )
        )
    )
    try:
        create_campaign_response = python_app.campaign.client.create_campaign(
            campaign_client.CreateCampaignRequest("100.00", "USD")
        )
        python_app.campaign.client.add_link(
            campaign_client.AddLinkRequest(
                create_campaign_response.campaign.campaign_id,
                "a",
                "https://ok.example/a",
            )
        )
        python_app.campaign.client.add_link(
            campaign_client.AddLinkRequest(
                create_campaign_response.campaign.campaign_id,
                "b",
                "https://ok.example/b",
            )
        )
        rows = python_app.reports.client.links_by_verdict(
            reports_client.LinksByVerdictRequest()
        ).links
        assert {r.slug for r in rows} == {"a", "b"}
        assert all(r.decision == "allowed" and r.reason == "ok" for r in rows)
    finally:
        python_app.close()


def test_blocked_destination_never_becomes_a_link() -> None:
    python_app = app.PythonApp(
        app.AppConfig(
            app.Spec(
                campaign=campaign_component.Config(campaign_component.Spec("memory")),
                linkpolicy=linkpolicy_component.Config(
                    linkpolicy_component.Spec("memory")
                ),
                reports=reports_component.Config(reports_component.Spec()),
                http=app.HttpConfig(app.HttpSpec("", 8080)),
            )
        )
    )
    try:
        create_campaign_response = python_app.campaign.client.create_campaign(
            campaign_client.CreateCampaignRequest("100.00", "USD")
        )
        try:
            python_app.campaign.client.add_link(
                campaign_client.AddLinkRequest(
                    create_campaign_response.campaign.campaign_id,
                    "bad",
                    "http://ok.example/a",
                )
            )
        except campaign_client.TargetBlocked:
            pass
        assert (
            python_app.reports.client.links_by_verdict(
                reports_client.LinksByVerdictRequest()
            ).links
            == ()
        )
    finally:
        python_app.close()
