from __future__ import annotations

from errors import (
    DomainError,
    DomainKind,
    InfraError,
    conflict,
    invalid,
    not_found,
    status_for,
)


def test_invalid_sets_validation_kind_code_and_field() -> None:
    e = invalid("bad_slug", "slug must be lowercase", field="slug")
    assert e.kind is DomainKind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_not_found_and_conflict_kinds() -> None:
    assert not_found("campaign_missing", "no such campaign").kind is DomainKind.NOT_FOUND
    assert conflict("duplicate_slug", "slug taken").kind is DomainKind.CONFLICT


def test_status_for_maps_each_kind() -> None:
    assert status_for(DomainKind.VALIDATION) == 422
    assert status_for(DomainKind.NOT_FOUND) == 404
    assert status_for(DomainKind.CONFLICT) == 409


def test_status_for_is_total_over_the_enum() -> None:
    for kind in DomainKind:
        assert status_for(kind) in (422, 404, 409)


def test_two_codes_share_one_kind() -> None:
    dup = conflict("duplicate_slug", "slug taken")
    deactivated = conflict("already_deactivated", "link already off")
    assert dup.kind is deactivated.kind is DomainKind.CONFLICT
    assert dup.code != deactivated.code


def test_chaining_preserves_cause_and_field() -> None:
    try:
        try:
            raise ValueError("low level")
        except ValueError as low:
            raise invalid("bad_amount", "amount invalid", field="amount") from low
    except DomainError as e:
        assert isinstance(e.__cause__, ValueError)
        assert e.field == "amount"
        assert e.code == "bad_amount"


def test_str_shows_code_and_field() -> None:
    assert str(invalid("bad_slug", "must be lowercase", field="slug")) == (
        "[bad_slug] (slug) must be lowercase"
    )
    assert str(not_found("campaign_missing", "no such campaign")) == (
        "[campaign_missing] no such campaign"
    )


def test_infra_is_not_a_domain_error() -> None:
    assert not issubclass(InfraError, DomainError)
    assert not isinstance(InfraError("db down"), DomainError)
