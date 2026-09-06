from __future__ import annotations

import catalog.adapters.gateways as gateways
import catalog.application.ports as ports


def test_a_reserved_name_is_refused_with_a_reason() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=("admin",))
    check_name_response = reserved_name_policy.check(ports.CheckNameRequest(name="admin"))
    assert (check_name_response.verdict, check_name_response.reason) == (
        ports.NameVerdict.RESERVED,
        "name is reserved",
    )


def test_a_free_name_is_allowed_without_a_reason() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=("admin",))
    check_name_response = reserved_name_policy.check(ports.CheckNameRequest(name="Anvil"))
    assert (check_name_response.verdict, check_name_response.reason) == (
        ports.NameVerdict.ALLOWED,
        "",
    )


def test_every_entry_in_the_reserved_list_is_refused() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=("admin", "root"))
    first = reserved_name_policy.check(ports.CheckNameRequest(name="admin"))
    second = reserved_name_policy.check(ports.CheckNameRequest(name="root"))
    assert (first.verdict, second.verdict) == (
        ports.NameVerdict.RESERVED,
        ports.NameVerdict.RESERVED,
    )


def test_a_reserved_name_is_matched_by_case() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=("admin",))
    check_name_response = reserved_name_policy.check(ports.CheckNameRequest(name="Admin"))
    assert check_name_response.verdict is ports.NameVerdict.ALLOWED


def test_a_name_that_merely_contains_a_reserved_entry_is_allowed() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=("admin",))
    check_name_response = reserved_name_policy.check(ports.CheckNameRequest(name="administrator"))
    assert check_name_response.verdict is ports.NameVerdict.ALLOWED


def test_a_policy_reserving_nothing_allows_every_name() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=())
    check_name_response = reserved_name_policy.check(ports.CheckNameRequest(name="admin"))
    assert (check_name_response.verdict, check_name_response.reason) == (
        ports.NameVerdict.ALLOWED,
        "",
    )


def test_an_empty_name_is_allowed_when_it_is_not_reserved() -> None:
    reserved_name_policy = gateways.ReservedNamePolicy(reserved=("admin",))
    check_name_response = reserved_name_policy.check(ports.CheckNameRequest(name=""))
    assert check_name_response.verdict is ports.NameVerdict.ALLOWED
