from __future__ import annotations

import pytest

import bootstrap.app as app
import bootstrap.config as config
import campaign.client.client as campaign_client
import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.client.client as reports_client
import reports.wiring.config as reports_config
from tesser.errors import DomainError


def test_an_app_builds_one_component_per_slice() -> None:
    built = app.App(config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    ))

    assert built.campaign.client is not None
    assert built.linkpolicy.client is not None
    assert built.reports.client is not None


def test_an_app_wires_its_components_to_each_other() -> None:
    built = app.App(config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    ))

    view = built.campaign.client.create_campaign(
        campaign_client.CreateCampaignRequest("100.00", "USD")
    )
    built.campaign.client.add_link(
        campaign_client.AddLinkRequest(view.campaign_id, "a", "https://ok.example/a")
    )

    rows = built.reports.client.links_by_verdict(reports_client.LinksByVerdictRequest()).links
    assert [row.slug for row in rows] == ["a"]


def test_an_app_refuses_a_slice_its_component_rejects() -> None:
    with pytest.raises(DomainError) as caught:
        app.App(config.Config(
        campaign=campaign_config.Config(storage=""),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    ))

    assert caught.value.code == "missing_coordinate"


def test_an_app_refuses_an_unsupported_backend() -> None:
    with pytest.raises(DomainError) as caught:
        app.App(config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="redis"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    ))

    assert caught.value.code == "unknown_backend"


def test_an_app_closes_its_components() -> None:
    built = app.App(config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    ))

    built.close()

    with pytest.raises(DomainError):
        built.campaign.client.get_campaign(
            campaign_client.GetCampaignRequest(campaign_id="0123456789abcdef")
        )


def test_an_app_carries_the_http_slice_its_host_reads() -> None:
    built = app.App(config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    ))

    assert built.http.port == 8080
