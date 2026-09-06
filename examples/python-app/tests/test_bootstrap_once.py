from __future__ import annotations

import app as app
import campaign.client as client
import tests.support as support


def test_graph_built_once_state_persists_across_calls() -> None:
    python_app = app.PythonApp(support.app_config())
    try:
        campaign_view = python_app.campaign.client.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        python_app.campaign.client.add_link(
            client.AddLinkRequest(campaign_view.campaign_id, "a", "https://ok.example/a")
        )
        python_app.campaign.client.add_link(
            client.AddLinkRequest(campaign_view.campaign_id, "b", "https://ok.example/b")
        )
        listed = python_app.campaign.client.list_links(client.ListLinksRequest()).links
        assert {v.slug for v in listed} == {"a", "b"}
    finally:
        python_app.close()


def test_a_component_is_built_once_and_reused_across_calls() -> None:
    python_app = app.PythonApp(support.app_config())
    try:
        first = python_app.campaign.client
        for _ in range(5):
            python_app.campaign.client.list_links(client.ListLinksRequest())
        assert python_app.campaign.client is first
    finally:
        python_app.close()


def test_two_apps_do_not_share_a_component() -> None:
    first = app.PythonApp(support.app_config())
    second = app.PythonApp(support.app_config())
    try:
        assert first.campaign.client is not second.campaign.client
    finally:
        first.close()
        second.close()
