from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain.campaign as campaign
import campaign.domain.short_link as short_link
import campaign.domain.values as values
from tesser.errors import DomainError, Kind


@ts.helper
def _window(start: str = "2026-01-01", end: str = "2026-02-01") -> values.DateWindowSpec:
    return values.DateWindowSpec(start=start, end=end)


@ts.helper
def _link(slug: str = "spring-sale", url: str = "https://x.com") -> short_link.ShortLinkSpec:
    return short_link.ShortLinkSpec(slug=slug, target_url=url)


@ts.helper
def _spec(slug: str = "spring-sale") -> campaign.CampaignSpec:
    return campaign.CampaignSpec(id="c1", window=_window(), links=(_link(slug),))


def test_campaign_valid() -> None:
    c = campaign.Campaign(_spec())
    assert c.id == "c1"
    assert len(c.links) == 1


def test_duplicate_slug_is_conflict() -> None:
    with pytest.raises(DomainError) as ei:
        campaign.Campaign(
            campaign.CampaignSpec(
                id="c1", window=_window(), links=(_link("dup-slug"), _link("dup-slug"))
            )
        )
    assert ei.value.kind is Kind.CONFLICT
    assert ei.value.code == "duplicate_slug"


def test_too_many_links_is_conflict() -> None:
    links = tuple(_link(f"link-{i}") for i in range(6))
    with pytest.raises(DomainError) as ei:
        campaign.Campaign(campaign.CampaignSpec(id="c1", window=_window(), links=links))
    assert ei.value.kind is Kind.CONFLICT
    assert ei.value.code == "too_many_links"


def test_bad_child_wrapped_with_index_keeps_kind_and_code() -> None:
    with pytest.raises(DomainError) as ei:
        campaign.Campaign(
            campaign.CampaignSpec(
                id="c1", window=_window(), links=(_link("ok-slug"), _link("BAD"))
            )
        )
    e = ei.value
    assert e.kind is Kind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "links[1].slug"
    assert isinstance(e.__cause__, DomainError)


def test_deactivate_missing_link_is_not_found() -> None:
    c = campaign.Campaign(_spec())
    with pytest.raises(DomainError) as ei:
        c.deactivate_link(values.Slug("no-such-link"))
    assert ei.value.kind is Kind.NOT_FOUND
    assert ei.value.code == "link_missing"


def test_links_accessor_returns_defensive_copy() -> None:
    c = campaign.Campaign(_spec())
    snapshot = c.links
    assert isinstance(snapshot, tuple)
    c.add_link(_link("summer-sale"))
    assert len(snapshot) == 1
    assert len(c.links) == 2
