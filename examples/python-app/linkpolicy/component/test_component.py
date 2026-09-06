from __future__ import annotations

import pytest

import linkpolicy.client as client
import linkpolicy.component as component
import tesser.errors as errors


def test_a_config_carries_the_storage_coordinate_it_was_given() -> None:
    assert component.Config(component.Spec("memory")).storage == "memory"


def test_a_config_carries_the_storage_coordinate_given_by_name() -> None:
    assert component.Config(component.Spec(storage="memory")).storage == "memory"


def test_a_config_accepts_an_absent_storage_coordinate() -> None:
    assert component.Config(component.Spec("")).storage == ""


def test_a_component_rejects_an_absent_storage_coordinate() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        component.LinkPolicy(component.Config(component.Spec("")))

    assert excinfo.value.code == "missing_coordinate"
    assert excinfo.value.message == "linkpolicy storage coordinate is required"


def test_a_component_rejects_a_backend_it_does_not_support() -> None:
    with pytest.raises(errors.DomainError) as excinfo:
        component.LinkPolicy(component.Config(component.Spec("redis")))

    assert excinfo.value.code == "unknown_backend"
    assert excinfo.value.message == "linkpolicy storage 'redis' not supported"


def test_a_component_exposes_a_client_that_checks_a_url() -> None:
    link_policy = component.LinkPolicy(component.Config(component.Spec("memory")))

    check_response = link_policy.client.check(client.CheckRequest("https://ok.example/x"))

    assert check_response.decision == "allowed"
    assert check_response.reason == "ok"


def test_a_component_exposes_a_client_that_denies_a_blocked_host() -> None:
    link_policy = component.LinkPolicy(component.Config(component.Spec("memory")))

    check_response = link_policy.client.check(client.CheckRequest("https://evil.example/x"))

    assert check_response.decision == "denied"
    assert check_response.reason == "host 'evil.example' is blocked"


def test_a_component_wires_its_service_to_the_repository_it_built() -> None:
    link_policy = component.LinkPolicy(component.Config(component.Spec("memory")))

    link_policy.client.check(client.CheckRequest("https://ok.example/x"))
    list_verdicts_response = link_policy.client.list_verdicts(client.ListVerdictsRequest())

    assert [
        (v.target_url, v.decision) for v in list_verdicts_response.verdicts
    ] == [("https://ok.example/x", "allowed")]


def test_each_component_gets_its_own_repository() -> None:
    first = component.LinkPolicy(component.Config(component.Spec("memory")))
    second = component.LinkPolicy(component.Config(component.Spec("memory")))

    first.client.check(client.CheckRequest("https://ok.example/x"))

    assert second.client.list_verdicts(client.ListVerdictsRequest()).verdicts == ()


def test_a_component_closes_what_it_built() -> None:
    link_policy = component.LinkPolicy(component.Config(component.Spec("memory")))

    link_policy.close()

    assert link_policy.client.list_verdicts(client.ListVerdictsRequest()).verdicts == ()
