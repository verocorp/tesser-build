from __future__ import annotations

import pytest

from bootstrap.config import Config, HttpConfig, from_env
import campaign.wiring.config as campaign_config
from tesser.errors import DomainError, Kind
import linkpolicy.wiring.config as linkpolicy_config
import reports.wiring.config as reports_config


def test_an_empty_environment_reads_as_the_declared_defaults() -> None:
    env: dict[str, str] = {}
    cfg = from_env(env.get)
    assert cfg.campaign.storage == ""
    assert cfg.linkpolicy.storage == ""
    assert cfg.http == HttpConfig("", 8080)


def test_every_coordinate_reads_from_its_own_variable() -> None:
    env = {
        "CAMPAIGN_STORAGE": "memory",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "9091",
    }
    cfg = from_env(env.get)
    assert cfg.campaign.storage == "memory"
    assert cfg.linkpolicy.storage == "memory"
    assert cfg.http == HttpConfig("127.0.0.1", 9091)


def test_an_empty_variable_falls_back_to_its_default() -> None:
    env = {"CAMPAIGN_STORAGE": "", "HTTP_HOST": "", "HTTP_PORT": ""}
    cfg = from_env(env.get)
    assert cfg.campaign.storage == ""
    assert cfg.http == HttpConfig("", 8080)


def test_a_non_numeric_port_is_rejected_by_code() -> None:
    env = {"HTTP_PORT": "eighty"}
    with pytest.raises(DomainError) as caught:
        from_env(env.get)
    assert caught.value.code == "bad_http_port"
    assert caught.value.kind is Kind.VALIDATION
    assert "eighty" in caught.value.message


def test_a_fractional_port_is_rejected_by_code() -> None:
    env = {"HTTP_PORT": "80.5"}
    with pytest.raises(DomainError) as caught:
        from_env(env.get)
    assert caught.value.code == "bad_http_port"


def test_a_port_rejection_names_no_other_coordinate() -> None:
    env = {"CAMPAIGN_STORAGE": "memory", "HTTP_PORT": "  "}
    with pytest.raises(DomainError) as caught:
        from_env(env.get)
    assert "HTTP_PORT" in caught.value.message
    assert "CAMPAIGN_STORAGE" not in caught.value.message


def test_a_config_built_without_an_http_coordinate_carries_the_default_one() -> None:
    cfg = Config(
        campaign=campaign_config.Config(storage="memory"),
        linkpolicy=linkpolicy_config.Config(storage="memory"),
        reports=reports_config.Config(),
    )
    assert cfg.http == HttpConfig("", 8080)
