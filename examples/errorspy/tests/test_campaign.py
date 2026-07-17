"""Cell D2 (aggregate collection invariants), X1 (index-wrapped child error keeps
kind + code), and a domain not_found on a missing link."""

from __future__ import annotations

import pytest

from domain.campaign import Campaign, CampaignSpec
from domain.short_link import ShortLinkSpec
from domain.values import DateWindowSpec, Slug
from errors import DomainError, DomainKind

_WINDOW = DateWindowSpec(start="2026-01-01", end="2026-02-01")


def _link(slug: str, url: str = "https://x.com") -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url=url)


def test_campaign_valid() -> None:
    c = Campaign("c1", CampaignSpec(window=_WINDOW, links=(_link("spring-sale"),)))
    assert c.id == "c1"
    assert len(c.links) == 1


def test_duplicate_slug_is_conflict() -> None:
    # D2 invariant.
    with pytest.raises(DomainError) as ei:
        Campaign(
            "c1", CampaignSpec(window=_WINDOW, links=(_link("dup-slug"), _link("dup-slug")))
        )
    assert ei.value.kind is DomainKind.CONFLICT
    assert ei.value.code == "duplicate_slug"


def test_too_many_links_is_conflict() -> None:
    links = tuple(_link(f"link-{i}") for i in range(6))
    with pytest.raises(DomainError) as ei:
        Campaign("c1", CampaignSpec(window=_WINDOW, links=links))
    assert ei.value.kind is DomainKind.CONFLICT
    assert ei.value.code == "too_many_links"


def test_bad_child_wrapped_with_index_keeps_kind_and_code() -> None:
    # X1: the child validation error survives the index wrap — kind, code, and
    # the underlying cause all intact; the field gains the collection path.
    with pytest.raises(DomainError) as ei:
        Campaign("c1", CampaignSpec(window=_WINDOW, links=(_link("ok-slug"), _link("BAD"))))
    e = ei.value
    assert e.kind is DomainKind.VALIDATION  # preserved through the wrap
    assert e.code == "bad_slug"  # preserved — client still sees the real problem
    assert e.field == "links[1].slug"  # index context added
    assert isinstance(e.__cause__, DomainError)  # chain fidelity


def test_deactivate_missing_link_is_not_found() -> None:
    c = Campaign("c1", CampaignSpec(window=_WINDOW, links=(_link("spring-sale"),)))
    with pytest.raises(DomainError) as ei:
        c.deactivate_link(Slug("no-such-link"))
    assert ei.value.kind is DomainKind.NOT_FOUND
    assert ei.value.code == "link_missing"


def test_links_accessor_returns_defensive_copy() -> None:
    c = Campaign("c1", CampaignSpec(window=_WINDOW, links=(_link("spring-sale"),)))
    snapshot = c.links
    assert isinstance(snapshot, tuple)  # immutable; backing list never leaks
    c.add_link(_link("summer-sale"))
    assert len(snapshot) == 1  # the earlier snapshot did not mutate
    assert len(c.links) == 2
