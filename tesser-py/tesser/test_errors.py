import pytest

import tesser.errors as errors


def test_constructors_carry_kind_code_and_message() -> None:
    assert errors.invalid("bad_name", "name is empty").kind is errors.Kind.VALIDATION
    assert errors.not_found("no_campaign", "campaign missing").kind is errors.Kind.NOT_FOUND
    assert errors.conflict("dup_slug", "slug taken").kind is errors.Kind.CONFLICT
    err = errors.invalid("bad_name", "name is empty")
    assert err.code == "bad_name"
    assert err.message == "name is empty"
    assert err.field is None
    assert err.problems == ()


def test_str_shows_code_and_message() -> None:
    assert str(errors.invalid("bad_name", "name is empty")) == "[bad_name] name is empty"


def test_str_shows_field_when_carried() -> None:
    err = errors.invalid("bad_name", "name is empty", field="name")
    assert str(err) == "[bad_name] (name) name is empty"


def test_wrap_keeps_kind_and_code_and_replaces_message() -> None:
    inner = errors.invalid("bad_name", "name is empty", field="name")
    outer = errors.wrap(inner, "campaign rejected")
    assert outer.kind is errors.Kind.VALIDATION
    assert outer.code == "bad_name"
    assert outer.message == "campaign rejected"
    assert outer.field == "name"


def test_wrap_field_override_wins() -> None:
    inner = errors.invalid("bad_name", "name is empty", field="name")
    assert errors.wrap(inner, "rejected", field="title").field == "title"


def test_collect_passes_when_every_field_is_valid() -> None:
    errors.collect(name=lambda: "ok", slug=lambda: "ok")


def test_collect_gathers_validation_problems_into_one_error() -> None:
    def bad_name() -> str:
        raise errors.invalid("bad_name", "empty")

    def bad_slug() -> str:
        raise errors.invalid("bad_slug", "empty", field="s")

    with pytest.raises(errors.DomainError) as caught:
        errors.collect(name=bad_name, slug=bad_slug)
    err = caught.value
    assert err.kind is errors.Kind.VALIDATION
    assert err.code == "validation_failed"
    assert err.problems == (
        errors.NeedsDesignFieldProblem("bad_name", "name", "empty"),
        errors.NeedsDesignFieldProblem("bad_slug", "s", "empty"),
    )


def test_collect_reraises_a_non_validation_error_unchanged() -> None:
    def missing_row() -> str:
        raise errors.not_found("no_row", "missing")

    with pytest.raises(errors.DomainError) as caught:
        errors.collect(name=missing_row)
    assert caught.value.kind is errors.Kind.NOT_FOUND
    assert caught.value.code == "no_row"


def test_status_for_is_total_over_the_kind_set() -> None:
    assert {kind: errors.status_for(kind) for kind in errors.Kind} == {
        errors.Kind.VALIDATION: 422,
        errors.Kind.NOT_FOUND: 404,
        errors.Kind.CONFLICT: 409,
    }


def test_exit_code_for_is_total_over_the_kind_set() -> None:
    assert {kind: errors.exit_code_for(kind) for kind in errors.Kind} == {
        errors.Kind.VALIDATION: 2,
        errors.Kind.NOT_FOUND: 1,
        errors.Kind.CONFLICT: 1,
    }


def test_infra_error_is_a_separate_channel() -> None:
    assert not issubclass(errors.InfraError, errors.DomainError)
    assert not issubclass(errors.DomainError, errors.InfraError)


def test_two_codes_share_one_kind() -> None:
    dup = errors.conflict("duplicate_slug", "slug taken")
    deactivated = errors.conflict("already_deactivated", "link already off")
    assert dup.kind is deactivated.kind is errors.Kind.CONFLICT
    assert dup.code != deactivated.code


def test_chaining_preserves_cause_and_field() -> None:
    try:
        try:
            raise ValueError("low level")
        except ValueError as low:
            raise errors.invalid("bad_amount", "amount invalid", field="amount") from low
    except errors.DomainError as e:
        assert isinstance(e.__cause__, ValueError)
        assert e.field == "amount"
        assert e.code == "bad_amount"
