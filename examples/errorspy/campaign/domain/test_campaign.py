from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain as domain
import tesser.errors as errors


@ts.helper
def _window_spec(start: str = "2026-01-01", end: str = "2026-02-01") -> domain.DateWindowSpec:
    return domain.DateWindowSpec(start=start, end=end)


@ts.helper
def _short_link_spec(
    slug: str = "spring-sale", url: str = "https://x.com"
) -> domain.ShortLinkSpec:
    return domain.ShortLinkSpec(slug=slug, target_url=url)


@ts.helper
def _campaign_spec(slug: str = "spring-sale") -> domain.CampaignSpec:
    return domain.CampaignSpec(
        id="c1", window=_window_spec(), links=(_short_link_spec(slug),)
    )


def test_slug_valid() -> None:
    assert str(domain.Slug("spring-sale")) == "spring-sale"


def test_slug_invalid_raises_validation() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.Slug("Bad Slug!")
    e = ei.value
    assert e.kind is errors.Kind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_target_url_invalid_raises_validation() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.TargetURL("ftp://example.com")
    assert ei.value.kind is errors.Kind.VALIDATION
    assert ei.value.code == "bad_target_url"
    assert ei.value.field == "target_url"


def test_date_window_valid() -> None:
    date_window = domain.DateWindow(domain.DateWindowSpec("2026-01-01", "2026-02-01"))
    assert str(date_window.start) == "2026-01-01"
    assert str(date_window.end) == "2026-02-01"


def test_date_window_bad_date_wraps_cause_with_field() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.DateWindow(domain.DateWindowSpec("nope", "2026-02-01"))
    e = ei.value
    assert e.kind is errors.Kind.VALIDATION
    assert e.code == "bad_date"
    assert e.field == "start"
    assert isinstance(e.__cause__, ValueError)


def test_date_window_order_invariant() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.DateWindow(domain.DateWindowSpec("2026-02-01", "2026-01-01"))
    assert ei.value.kind is errors.Kind.VALIDATION
    assert ei.value.code == "window_order"


def test_campaign_id_valid() -> None:
    assert str(domain.CampaignID("c1")) == "c1"
    assert domain.CampaignID("c1") == domain.CampaignID("c1")
    assert domain.CampaignID("c1") != domain.CampaignID("c2")


def test_campaign_id_empty_raises_validation() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.CampaignID("")
    assert ei.value.kind is errors.Kind.VALIDATION
    assert ei.value.code == "bad_campaign_id"
    assert ei.value.field == "campaign_id"


def test_short_link_valid() -> None:
    short_link = domain.ShortLink(_short_link_spec())
    assert str(short_link.slug) == "spring-sale"
    assert short_link.status == domain.LinkStatus("active")


def test_child_error_propagates_unchanged() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.ShortLink(_short_link_spec(slug="BAD"))
    e = ei.value
    assert e.kind is errors.Kind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_deactivate_then_deactivate_is_conflict() -> None:
    short_link = domain.ShortLink(_short_link_spec())
    short_link.deactivate()
    assert short_link.status == domain.LinkStatus("inactive")
    with pytest.raises(errors.DomainError) as ei:
        short_link.deactivate()
    assert ei.value.kind is errors.Kind.CONFLICT
    assert ei.value.code == "already_deactivated"


def test_identity_equality_by_slug() -> None:
    first = domain.ShortLink(_short_link_spec())
    second = domain.ShortLink(_short_link_spec(url="https://y.com"))
    assert first == second
    assert hash(first) == hash(second)


def test_campaign_valid() -> None:
    campaign = domain.Campaign(_campaign_spec())
    assert campaign.id == "c1"
    assert len(campaign.links) == 1


def test_duplicate_slug_is_conflict() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.Campaign(
            domain.CampaignSpec(
                id="c1",
                window=_window_spec(),
                links=(_short_link_spec("dup-slug"), _short_link_spec("dup-slug")),
            )
        )
    assert ei.value.kind is errors.Kind.CONFLICT
    assert ei.value.code == "duplicate_slug"


def test_too_many_links_is_conflict() -> None:
    links = tuple(_short_link_spec(f"link-{i}") for i in range(6))
    with pytest.raises(errors.DomainError) as ei:
        domain.Campaign(domain.CampaignSpec(id="c1", window=_window_spec(), links=links))
    assert ei.value.kind is errors.Kind.CONFLICT
    assert ei.value.code == "too_many_links"


def test_bad_child_wrapped_with_index_keeps_kind_and_code() -> None:
    with pytest.raises(errors.DomainError) as ei:
        domain.Campaign(
            domain.CampaignSpec(
                id="c1",
                window=_window_spec(),
                links=(_short_link_spec("ok-slug"), _short_link_spec("BAD")),
            )
        )
    e = ei.value
    assert e.kind is errors.Kind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "links[1].slug"
    assert isinstance(e.__cause__, errors.DomainError)


def test_deactivate_missing_link_is_not_found() -> None:
    campaign = domain.Campaign(_campaign_spec())
    with pytest.raises(errors.DomainError) as ei:
        campaign.deactivate_link(domain.Slug("no-such-link"))
    assert ei.value.kind is errors.Kind.NOT_FOUND
    assert ei.value.code == "link_missing"


def test_links_accessor_returns_defensive_copy() -> None:
    campaign = domain.Campaign(_campaign_spec())
    snapshot = campaign.links
    assert isinstance(snapshot, tuple)
    campaign.add_link(_short_link_spec("summer-sale"))
    assert len(snapshot) == 1
    assert len(campaign.links) == 2
