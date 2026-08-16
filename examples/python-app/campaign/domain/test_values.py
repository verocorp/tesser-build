from __future__ import annotations

import pytest

import campaign.domain.values as values
from tesser.errors import DomainError, Kind


def test_campaign_id_round_trips_through_its_canonical_exit() -> None:
    id = values.CampaignID("0123456789abcdef")

    assert values.CampaignID(str(id)) == id


def test_campaign_ids_with_the_same_digits_are_the_same_value() -> None:
    a = values.CampaignID("0123456789abcdef")
    b = values.CampaignID("0123456789abcdef")

    assert a == b
    assert hash(a) == hash(b)


def test_campaign_ids_with_different_digits_are_different_values() -> None:
    a = values.CampaignID("0123456789abcdef")
    b = values.CampaignID("fedcba9876543210")

    assert a != b


@pytest.mark.parametrize(
    "value", ["", "0123456789abcde", "0123456789abcdef0", "0123456789ABCDEF", "0123456789abcdeg"]
)
def test_a_campaign_id_that_is_not_sixteen_lowercase_hex_is_rejected(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        values.CampaignID(value)

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "invalid_campaign_id"


@pytest.mark.parametrize("value", ["active", "inactive"])
def test_a_link_status_admits_the_two_declared_states(value: str) -> None:
    status = values.LinkStatus(value)

    assert values.LinkStatus(str(status)) == status


def test_the_two_link_states_are_different_values() -> None:
    assert values.LinkStatus("active") != values.LinkStatus("inactive")


@pytest.mark.parametrize("value", ["", "ACTIVE", "paused", "Active", " active"])
def test_a_link_status_outside_the_declared_states_is_rejected(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        values.LinkStatus(value)

    assert caught.value.code == "invalid_link_status"
    assert "active, inactive" in caught.value.message


def test_a_target_url_round_trips_through_its_canonical_exit() -> None:
    target = values.TargetURL("https://ok.example/x?a=1#frag")

    assert values.TargetURL(str(target)) == target


def test_target_urls_differing_only_in_path_are_different_values() -> None:
    assert values.TargetURL("https://ok.example/a") != values.TargetURL("https://ok.example/b")


def test_a_target_url_carrying_a_control_character_is_rejected() -> None:
    with pytest.raises(DomainError) as caught:
        values.TargetURL("https://ok.example/\r\nX-Injected: yes")

    assert caught.value.code == "invalid_target_url"
    assert "control characters" in caught.value.message


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ftp://ok.example/x",
        "javascript:alert(1)",
        "https:///nohost",
        "/relative/path",
        "ok.example/x",
    ],
)
def test_a_target_url_that_is_not_http_with_a_host_is_rejected(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        values.TargetURL(value)

    assert caught.value.kind is Kind.VALIDATION
    assert caught.value.code == "invalid_target_url"


def test_the_slug_re_exported_here_round_trips_through_its_canonical_exit() -> None:
    slug = values.Slug("spring-sale")

    assert values.Slug(str(slug)) == slug


@pytest.mark.parametrize("value", ["", "Promo", "promo sale", "-promo", "promo-", "promo_sale"])
def test_the_slug_re_exported_here_still_rejects_a_malformed_value(value: str) -> None:
    with pytest.raises(DomainError) as caught:
        values.Slug(value)

    assert caught.value.code == "invalid_slug"
