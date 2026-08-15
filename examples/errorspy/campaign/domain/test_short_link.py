from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, Kind


@ts.helper
def _spec(slug: str = "spring-sale", url: str = "https://x.com") -> short_link.ShortLinkSpec:
    return short_link.ShortLinkSpec(slug=slug, target_url=url)


def test_short_link_valid() -> None:
    link = short_link.ShortLink(_spec())
    assert str(link.slug) == "spring-sale"
    assert link.status == values.LinkStatus("active")


def test_child_error_propagates_unchanged() -> None:
    with pytest.raises(DomainError) as ei:
        short_link.ShortLink(_spec(slug="BAD"))
    e = ei.value
    assert e.kind is Kind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_deactivate_then_deactivate_is_conflict() -> None:
    link = short_link.ShortLink(_spec())
    link.deactivate()
    assert link.status == values.LinkStatus("inactive")
    with pytest.raises(DomainError) as ei:
        link.deactivate()
    assert ei.value.kind is Kind.CONFLICT
    assert ei.value.code == "already_deactivated"


def test_identity_equality_by_slug() -> None:
    a = short_link.ShortLink(_spec())
    b = short_link.ShortLink(_spec(url="https://y.com"))
    assert a == b
    assert hash(a) == hash(b)
