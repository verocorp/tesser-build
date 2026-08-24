from __future__ import annotations

import pytest

import app.app as app
import app.config as config
import campaign.client.client as campaign_client
import campaign.component.config as campaign_config
import linkpolicy.component.config as linkpolicy_config
import reports.client.client as reports_client
import reports.component.config as reports_config
import tesser.errors as errors


def test_an_app_builds_one_component_per_slice() -> None:
    built = app.App(
        config.Config(
            config.Spec(
                campaign=campaign_config.Config(campaign_config.Spec(storage="memory")),
                linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="memory")),
                reports=reports_config.Config(reports_config.Spec()),
                http=config.HttpConfig(config.HttpSpec("", 8080)),
            )
        )
    )

    assert built.campaign.client is not None
    assert built.linkpolicy.client is not None
    assert built.reports.client is not None


def test_an_app_wires_its_components_to_each_other() -> None:
    built = app.App(
        config.Config(
            config.Spec(
                campaign=campaign_config.Config(campaign_config.Spec(storage="memory")),
                linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="memory")),
                reports=reports_config.Config(reports_config.Spec()),
                http=config.HttpConfig(config.HttpSpec("", 8080)),
            )
        )
    )

    view = built.campaign.client.create_campaign(
        campaign_client.CreateCampaignRequest("100.00", "USD")
    )
    built.campaign.client.add_link(
        campaign_client.AddLinkRequest(view.campaign_id, "a", "https://ok.example/a")
    )

    rows = built.reports.client.links_by_verdict(reports_client.LinksByVerdictRequest()).links
    assert [row.slug for row in rows] == ["a"]


def test_an_app_refuses_a_slice_its_component_rejects() -> None:
    with pytest.raises(errors.DomainError) as caught:
        app.App(
            config.Config(
                config.Spec(
                    campaign=campaign_config.Config(campaign_config.Spec(storage="")),
                    linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="memory")),
                    reports=reports_config.Config(reports_config.Spec()),
                    http=config.HttpConfig(config.HttpSpec("", 8080)),
                )
            )
        )

    assert caught.value.code == "missing_coordinate"


def test_an_app_refuses_an_unsupported_backend() -> None:
    with pytest.raises(errors.DomainError) as caught:
        app.App(
            config.Config(
                config.Spec(
                    campaign=campaign_config.Config(campaign_config.Spec(storage="memory")),
                    linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="redis")),
                    reports=reports_config.Config(reports_config.Spec()),
                    http=config.HttpConfig(config.HttpSpec("", 8080)),
                )
            )
        )

    assert caught.value.code == "unknown_backend"


def test_an_app_carries_the_http_slice_its_host_reads() -> None:
    built = app.App(
        config.Config(
            config.Spec(
                campaign=campaign_config.Config(campaign_config.Spec(storage="memory")),
                linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="memory")),
                reports=reports_config.Config(reports_config.Spec()),
                http=config.HttpConfig(config.HttpSpec("127.0.0.1", 9091)),
            )
        )
    )

    assert built.http.host == "127.0.0.1"
    assert built.http.port == 9091
