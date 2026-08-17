from __future__ import annotations

import app.config as config
import campaign.component.config as campaign_config
import linkpolicy.component.config as linkpolicy_config
import reports.component.config as reports_config


def test_a_config_carries_one_slice_per_component() -> None:
    cfg = config.Config(
        config.Spec(
            campaign=campaign_config.Config(campaign_config.Spec(storage="memory")),
            linkpolicy=linkpolicy_config.Config(linkpolicy_config.Spec(storage="postgres")),
            reports=reports_config.Config(reports_config.Spec()),
            http=config.HttpConfig(config.HttpSpec("", 8080)),
        )
    )

    assert cfg.campaign.storage == "memory"
    assert cfg.linkpolicy.storage == "postgres"


def test_an_http_config_carries_the_coordinate_it_was_given() -> None:
    http = config.HttpConfig(config.HttpSpec("127.0.0.1", 9091))

    assert http.host == "127.0.0.1"
    assert http.port == 9091
