from __future__ import annotations

import pytest

import linkpolicy.client.client as client
import linkpolicy.wiring.config as config
import linkpolicy.wiring.wire as wire
from tesser.errors import DomainError


def test_a_component_rejects_an_absent_storage_coordinate() -> None:
    with pytest.raises(DomainError) as excinfo:
        wire.LinkPolicy(config.Config(""))

    assert excinfo.value.code == "missing_coordinate"
    assert excinfo.value.message == "linkpolicy storage coordinate is required"


def test_a_component_rejects_a_backend_it_does_not_support() -> None:
    with pytest.raises(DomainError) as excinfo:
        wire.LinkPolicy(config.Config("redis"))

    assert excinfo.value.code == "unknown_backend"
    assert excinfo.value.message == "linkpolicy storage 'redis' not supported"


def test_a_component_exposes_a_client_that_checks_a_url() -> None:
    built = wire.LinkPolicy(config.Config("memory"))

    resp = built.client.check(client.CheckRequest("https://ok.example/x"))

    assert resp.allowed is True
    assert resp.reason == "ok"


def test_a_component_exposes_a_client_that_denies_a_blocked_host() -> None:
    built = wire.LinkPolicy(config.Config("memory"))

    resp = built.client.check(client.CheckRequest("https://evil.example/x"))

    assert resp.allowed is False
    assert resp.reason == "host 'evil.example' is blocked"


def test_a_component_wires_its_service_to_the_repository_it_built() -> None:
    built = wire.LinkPolicy(config.Config("memory"))

    built.client.check(client.CheckRequest("https://ok.example/x"))
    listed = built.client.list_verdicts(client.ListVerdictsRequest())

    assert [(v.target_url, v.allowed) for v in listed.verdicts] == [("https://ok.example/x", True)]


def test_each_component_gets_its_own_repository() -> None:
    first = wire.LinkPolicy(config.Config("memory"))
    second = wire.LinkPolicy(config.Config("memory"))

    first.client.check(client.CheckRequest("https://ok.example/x"))

    assert second.client.list_verdicts(client.ListVerdictsRequest()).verdicts == ()


def test_a_component_closes_what_it_built() -> None:
    built = wire.LinkPolicy(config.Config("memory"))

    built.close()

    assert built.client.list_verdicts(client.ListVerdictsRequest()).verdicts == ()
