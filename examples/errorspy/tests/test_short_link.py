from __future__ import annotations

import pytest

from domain.short_link import ShortLink, ShortLinkSpec
from errors import DomainError, DomainKind


def _valid() -> ShortLink:
    return ShortLink(ShortLinkSpec(slug="spring-sale", target_url="https://x.com"))


def test_short_link_valid() -> None:
    link = _valid()
    assert str(link.slug) == "spring-sale"
    assert link.active is True


def test_child_error_propagates_unchanged() -> None:
    with pytest.raises(DomainError) as ei:
        ShortLink(ShortLinkSpec(slug="BAD", target_url="https://x.com"))
    e = ei.value
    assert e.kind is DomainKind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_deactivate_then_deactivate_is_conflict() -> None:
    link = _valid()
    link.deactivate()
    assert link.active is False
    with pytest.raises(DomainError) as ei:
        link.deactivate()
    assert ei.value.kind is DomainKind.CONFLICT
    assert ei.value.code == "already_deactivated"


def test_identity_equality_by_slug() -> None:
    a = _valid()
    b = ShortLink(ShortLinkSpec(slug="spring-sale", target_url="https://y.com"))
    assert a == b
    assert hash(a) == hash(b)
