from __future__ import annotations

import catalog.adapters.gateways.name_reserved as name_reserved
import catalog.application.ports.name_policy as name_policy


def test_a_reserved_name_is_refused_with_a_reason() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=("admin",))
    checked = policy.check(name_policy.CheckNameRequest(name="admin"))
    assert (checked.verdict, checked.reason) == (
        name_policy.NameVerdict.RESERVED,
        "name is reserved",
    )


def test_a_free_name_is_allowed_without_a_reason() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=("admin",))
    checked = policy.check(name_policy.CheckNameRequest(name="Anvil"))
    assert (checked.verdict, checked.reason) == (name_policy.NameVerdict.ALLOWED, "")


def test_every_entry_in_the_reserved_list_is_refused() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=("admin", "root"))
    first = policy.check(name_policy.CheckNameRequest(name="admin"))
    second = policy.check(name_policy.CheckNameRequest(name="root"))
    assert (first.verdict, second.verdict) == (
        name_policy.NameVerdict.RESERVED,
        name_policy.NameVerdict.RESERVED,
    )


def test_a_reserved_name_is_matched_by_case() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=("admin",))
    checked = policy.check(name_policy.CheckNameRequest(name="Admin"))
    assert checked.verdict is name_policy.NameVerdict.ALLOWED


def test_a_name_that_merely_contains_a_reserved_entry_is_allowed() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=("admin",))
    checked = policy.check(name_policy.CheckNameRequest(name="administrator"))
    assert checked.verdict is name_policy.NameVerdict.ALLOWED


def test_a_policy_reserving_nothing_allows_every_name() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=())
    checked = policy.check(name_policy.CheckNameRequest(name="admin"))
    assert (checked.verdict, checked.reason) == (name_policy.NameVerdict.ALLOWED, "")


def test_an_empty_name_is_allowed_when_it_is_not_reserved() -> None:
    policy = name_reserved.ReservedNamePolicy(reserved=("admin",))
    checked = policy.check(name_policy.CheckNameRequest(name=""))
    assert checked.verdict is name_policy.NameVerdict.ALLOWED
