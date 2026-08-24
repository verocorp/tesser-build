from __future__ import annotations

import pytest

import campaign.domain.values as values
import tesser.errors as errors


def test_slug_valid() -> None:
    assert str(values.Slug("spring-sale")) == "spring-sale"


def test_slug_invalid_raises_validation() -> None:
    with pytest.raises(errors.DomainError) as ei:
        values.Slug("Bad Slug!")
    e = ei.value
    assert e.kind is errors.Kind.VALIDATION
    assert e.code == "bad_slug"
    assert e.field == "slug"


def test_target_url_invalid_raises_validation() -> None:
    with pytest.raises(errors.DomainError) as ei:
        values.TargetURL("ftp://example.com")
    assert ei.value.kind is errors.Kind.VALIDATION
    assert ei.value.code == "bad_target_url"
    assert ei.value.field == "target_url"


def test_date_window_valid() -> None:
    w = values.DateWindow("2026-01-01", "2026-02-01")
    assert str(w.start) == "2026-01-01"
    assert str(w.end) == "2026-02-01"


def test_date_window_bad_date_wraps_cause_with_field() -> None:
    with pytest.raises(errors.DomainError) as ei:
        values.DateWindow("nope", "2026-02-01")
    e = ei.value
    assert e.kind is errors.Kind.VALIDATION
    assert e.code == "bad_date"
    assert e.field == "start"
    assert isinstance(e.__cause__, ValueError)


def test_date_window_order_invariant() -> None:
    with pytest.raises(errors.DomainError) as ei:
        values.DateWindow("2026-02-01", "2026-01-01")
    assert ei.value.kind is errors.Kind.VALIDATION
    assert ei.value.code == "window_order"


def test_campaign_id_valid() -> None:
    assert str(values.CampaignID("c1")) == "c1"
    assert values.CampaignID("c1") == values.CampaignID("c1")
    assert values.CampaignID("c1") != values.CampaignID("c2")


def test_campaign_id_empty_raises_validation() -> None:
    with pytest.raises(errors.DomainError) as ei:
        values.CampaignID("")
    assert ei.value.kind is errors.Kind.VALIDATION
    assert ei.value.code == "bad_campaign_id"
    assert ei.value.field == "campaign_id"
