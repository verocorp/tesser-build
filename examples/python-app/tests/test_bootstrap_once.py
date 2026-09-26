from __future__ import annotations

import app as app
import campaign.client as campaign_client

import campaign.component as campaign_component
import linkpolicy.component as linkpolicy_component
import reports.component as reports_component


def test_graph_built_once_state_persists_across_calls() -> None:
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
        listed = python_app.campaign.client.list_links(
            campaign_client.ListLinksRequest()
        ).links
        assert {v.slug for v in listed} == {"a", "b"}
    finally:
        python_app.close()


def test_a_component_is_built_once_and_reused_across_calls() -> None:
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
        first = python_app.campaign.client
        for _ in range(5):
            python_app.campaign.client.list_links(campaign_client.ListLinksRequest())
        assert python_app.campaign.client is first
    finally:
        python_app.close()


def test_two_apps_do_not_share_a_component() -> None:
    first = app.PythonApp(
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
    second = app.PythonApp(
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
        assert first.campaign.client is not second.campaign.client
    finally:
        first.close()
        second.close()
