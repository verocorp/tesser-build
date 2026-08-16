from __future__ import annotations

import bootstrap.config as config
import campaign.wiring.config as campaign_config
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config


def test_a_config_carries_one_slice_per_component() -> None:
    cfg = config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="postgres"),
        reports=reports_config.Config(),
        http=config.HttpConfig("127.0.0.1", 9091),
    )

    assert cfg.campaign.storage == "memory"
    assert cfg.linkpolicy.storage == "postgres"


def test_an_http_config_carries_the_coordinate_it_was_given() -> None:
    http = config.HttpConfig("127.0.0.1", 9091)

    assert http.host == "127.0.0.1"
    assert http.port == 9091


def test_a_config_slice_is_the_one_its_component_reads() -> None:
    cfg = config.Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
        http=config.HttpConfig("", 8080),
    )

    assert cfg.http.host == ""
    assert cfg.http.port == 8080
