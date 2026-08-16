from __future__ import annotations

import pytest

import linkpolicy.adapters.gateways.repo_memory as repo_memory
import linkpolicy.application.ports.verdict_repository as verdict_repository
import linkpolicy.client.client as client
import linkpolicy.wiring.config as config
import linkpolicy.wiring.wire as wire
from tesser.errors import DomainError


def test_repo_for_memory_builds_an_in_memory_repository() -> None:
    repo, closeable = wire.repo_for(config.Config("memory"))

    assert isinstance(repo, repo_memory.InMemoryVerdictRepository)
    assert closeable is repo


def test_repo_for_memory_builds_an_empty_repository() -> None:
    repo, _ = wire.repo_for(config.Config("memory"))

    assert repo.all(verdict_repository.ListVerdictsRequest()).verdicts == ()


def test_repo_for_rejects_an_absent_storage_coordinate() -> None:
    with pytest.raises(DomainError) as excinfo:
        wire.repo_for(config.Config(""))

    assert excinfo.value.code == "missing_coordinate"
    assert excinfo.value.message == "linkpolicy storage coordinate is required"


def test_repo_for_rejects_a_backend_it_does_not_support() -> None:
    with pytest.raises(DomainError) as excinfo:
        wire.repo_for(config.Config("redis"))

    assert excinfo.value.code == "unknown_backend"
    assert excinfo.value.message == "linkpolicy storage 'redis' not supported"


def test_build_returns_a_client_that_checks_a_url() -> None:
    built, _ = wire.build(config.Config("memory"))

    resp = built.check(client.CheckRequest("https://ok.example/x"))

    assert resp.allowed is True
    assert resp.reason == "ok"


def test_build_returns_a_client_that_denies_a_blocked_host() -> None:
    built, _ = wire.build(config.Config("memory"))

    resp = built.check(client.CheckRequest("https://evil.example/x"))

    assert resp.allowed is False
    assert resp.reason == "host 'evil.example' is blocked"


def test_build_wires_the_service_to_the_repository_it_built() -> None:
    built, _ = wire.build(config.Config("memory"))

    built.check(client.CheckRequest("https://ok.example/x"))
    listed = built.list_verdicts(client.ListVerdictsRequest())

    assert [(v.target_url, v.allowed) for v in listed.verdicts] == [
        ("https://ok.example/x", True)
    ]


def test_each_build_gets_its_own_repository() -> None:
    first, _ = wire.build(config.Config("memory"))
    second, _ = wire.build(config.Config("memory"))

    first.check(client.CheckRequest("https://ok.example/x"))

    assert second.list_verdicts(client.ListVerdictsRequest()).verdicts == ()


def test_build_hands_back_the_repository_as_its_closeable() -> None:
    _, closeable = wire.build(config.Config("memory"))

    assert isinstance(closeable, repo_memory.InMemoryVerdictRepository)

    closeable.close()

    assert closeable.close_count == 1


def test_build_rejects_a_backend_it_does_not_support() -> None:
    with pytest.raises(DomainError) as excinfo:
        wire.build(config.Config("redis"))

    assert excinfo.value.code == "unknown_backend"


def test_build_rejects_an_absent_storage_coordinate() -> None:
    with pytest.raises(DomainError) as excinfo:
        wire.build(config.Config(""))

    assert excinfo.value.code == "missing_coordinate"
