from __future__ import annotations

from datetime import date

import pytest

from domain.values import DateWindow, DateWindowSpec, Slug, TargetURL
from errors import DomainError, DomainKind


def test_slug_valid() -> None:
    assert str(Slug("spring-sale")) == "spring-sale"


def test_slug_invalid_raises_validation() -> None:
    with pytest.raises(DomainError) as ei:
        Slug("Bad Slug!")
    e = ei.value
    assert e.kind is DomainKind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_target_url_invalid_raises_validation() -> None:
    with pytest.raises(DomainError) as ei:
        TargetURL("ftp://example.com")
    assert ei.value.kind is DomainKind.VALIDATION
    assert ei.value.code == "bad_target_url"
    assert ei.value.field == "target_url"


def test_date_window_valid() -> None:
    w = DateWindow.from_spec(DateWindowSpec(start="2026-01-01", end="2026-02-01"))
    assert str(w) == "[2026-01-01, 2026-02-01)"


def test_date_window_bad_date_wraps_cause_with_field() -> None:
    with pytest.raises(DomainError) as ei:
        DateWindow.from_spec(DateWindowSpec(start="nope", end="2026-02-01"))
    e = ei.value
    assert e.kind is DomainKind.VALIDATION
    assert e.code == "bad_date"
    assert e.field == "start"
    assert isinstance(e.__cause__, ValueError)


def test_date_window_order_invariant() -> None:
    with pytest.raises(DomainError) as ei:
        DateWindow.from_spec(DateWindowSpec(start="2026-02-01", end="2026-01-01"))
    assert ei.value.kind is DomainKind.VALIDATION
    assert ei.value.code == "window_order"
