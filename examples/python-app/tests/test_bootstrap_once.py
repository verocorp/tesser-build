from __future__ import annotations

import bootstrap.app as app
import campaign.client.client as client
from tests.support import app_config


def test_graph_built_once_state_persists_across_calls() -> None:
    built = app.App(app_config())
    try:
        view = built.campaign.client.create_campaign(client.CreateCampaignRequest("100.00", "USD"))
        built.campaign.client.add_link(
            client.AddLinkRequest(view.campaign_id, "a", "https://ok.example/a")
        )
        built.campaign.client.add_link(
            client.AddLinkRequest(view.campaign_id, "b", "https://ok.example/b")
        )
        listed = built.campaign.client.list_links(client.ListLinksRequest()).links
        assert {v.slug for v in listed} == {"a", "b"}
    finally:
        built.close()


def test_a_component_is_built_once_and_reused_across_calls() -> None:
    built = app.App(app_config())
    try:
        first = built.campaign.client
        for _ in range(5):
            built.campaign.client.list_links(client.ListLinksRequest())
        assert built.campaign.client is first
    finally:
        built.close()


def test_two_apps_do_not_share_a_component() -> None:
    first = app.App(app_config())
    second = app.App(app_config())
    try:
        assert first.campaign.client is not second.campaign.client
    finally:
        first.close()
        second.close()
