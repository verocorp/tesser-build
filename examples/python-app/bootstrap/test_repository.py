from __future__ import annotations

import pytest

import bootstrap.repository as repository
from tesser.errors import DomainError, Kind


def test_every_coordinate_reads_from_its_own_variable() -> None:
    cfg = repository.EnvConfigRepository(
        {
            "CAMPAIGN_STORAGE": "memory",
            "LINKPOLICY_STORAGE": "postgres",
            "HTTP_HOST": "127.0.0.1",
            "HTTP_PORT": "9091",
        }
    ).get()

    assert cfg.campaign.storage == "memory"
    assert cfg.linkpolicy.storage == "postgres"
    assert cfg.http.host == "127.0.0.1"
    assert cfg.http.port == 9091


def test_an_empty_environment_is_refused_rather_than_defaulted() -> None:
    with pytest.raises(DomainError) as caught:
        repository.EnvConfigRepository({}).get()

    assert caught.value.code == "missing_env"
    assert caught.value.kind is Kind.VALIDATION
    assert "CAMPAIGN_STORAGE" in caught.value.message


def test_a_missing_variable_is_named_in_the_refusal() -> None:
    with pytest.raises(DomainError) as caught:
        repository.EnvConfigRepository({"CAMPAIGN_STORAGE": "memory"}).get()

    assert "LINKPOLICY_STORAGE" in caught.value.message


def test_an_empty_variable_is_a_coordinate_the_component_refuses() -> None:
    cfg = repository.EnvConfigRepository(
        {
            "CAMPAIGN_STORAGE": "",
            "LINKPOLICY_STORAGE": "memory",
            "HTTP_HOST": "",
            "HTTP_PORT": "8080",
        }
    ).get()

    assert cfg.campaign.storage == ""


def test_a_non_numeric_port_is_rejected_by_code() -> None:
    with pytest.raises(DomainError) as caught:
        repository.EnvConfigRepository(
            {
                "CAMPAIGN_STORAGE": "memory",
                "LINKPOLICY_STORAGE": "memory",
                "HTTP_HOST": "",
                "HTTP_PORT": "eighty",
            }
        ).get()

    assert caught.value.code == "bad_http_port"
    assert caught.value.kind is Kind.VALIDATION
    assert "eighty" in caught.value.message


def test_a_fractional_port_is_rejected_by_code() -> None:
    with pytest.raises(DomainError) as caught:
        repository.EnvConfigRepository(
            {
                "CAMPAIGN_STORAGE": "memory",
                "LINKPOLICY_STORAGE": "memory",
                "HTTP_HOST": "",
                "HTTP_PORT": "80.5",
            }
        ).get()

    assert caught.value.code == "bad_http_port"


def test_a_port_rejection_names_no_other_coordinate() -> None:
    with pytest.raises(DomainError) as caught:
        repository.EnvConfigRepository(
            {
                "CAMPAIGN_STORAGE": "memory",
                "LINKPOLICY_STORAGE": "memory",
                "HTTP_HOST": "",
                "HTTP_PORT": "  ",
            }
        ).get()

    assert "HTTP_PORT" in caught.value.message
    assert "CAMPAIGN_STORAGE" not in caught.value.message
