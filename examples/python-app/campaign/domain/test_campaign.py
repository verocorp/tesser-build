from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain as domain
import tesser.errors as errors


@ts.helper
def _short_link_spec(
    slug: str = "spring-sale",
    target_url: str = "https://ok.example/x",
    active: bool = True,
) -> domain.ShortLinkSpec:
    return domain.ShortLinkSpec(slug=slug, target_url=target_url, active=active)


def test_a_short_link_carries_every_field_of_its_spec() -> None:
    short_link_spec = _short_link_spec()

    short_link = domain.ShortLink(short_link_spec)

    assert short_link.slug == domain.Slug(short_link_spec.slug)
    assert short_link.target_url == domain.TargetURL(short_link_spec.target_url)
    assert short_link.status == domain.LinkStatus(domain.LinkState.ACTIVE)


def test_a_short_link_built_inactive_starts_inactive() -> None:
    short_link = domain.ShortLink(_short_link_spec(active=False))

    assert short_link.status == domain.LinkStatus(domain.LinkState.INACTIVE)


def test_deactivate_turns_an_active_link_inactive() -> None:
    short_link = domain.ShortLink(_short_link_spec(active=True))

    short_link.deactivate()

    assert short_link.status == domain.LinkStatus(domain.LinkState.INACTIVE)


def test_deactivate_leaves_an_already_inactive_link_inactive() -> None:
    short_link = domain.ShortLink(_short_link_spec(active=False))

    short_link.deactivate()

    assert short_link.status == domain.LinkStatus(domain.LinkState.INACTIVE)


def test_deactivate_leaves_the_slug_and_target_untouched() -> None:
    short_link = domain.ShortLink(_short_link_spec(slug="promo", target_url="https://ok.example/a"))

    short_link.deactivate()

    assert short_link.slug == domain.Slug("promo")
    assert short_link.target_url == domain.TargetURL("https://ok.example/a")


def test_a_short_link_is_identified_by_its_slug() -> None:
    short_link = domain.ShortLink(_short_link_spec(slug="promo"))

    assert short_link.identity == domain.Slug("promo")


def test_two_short_links_with_the_same_slug_are_the_same_entity() -> None:
    a = domain.ShortLink(_short_link_spec(slug="promo", target_url="https://ok.example/a"))
    b = domain.ShortLink(_short_link_spec(slug="promo", target_url="https://ok.example/b", active=False))

    assert a == b
    assert hash(a) == hash(b)


def test_two_short_links_with_different_slugs_are_different_entities() -> None:
    a = domain.ShortLink(_short_link_spec(slug="promo"))
    b = domain.ShortLink(_short_link_spec(slug="sale"))

    assert a != b


@pytest.mark.parametrize("slug", ["", "Promo", "promo sale", "-promo"])
def test_a_short_link_refuses_a_malformed_slug(slug: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.ShortLink(_short_link_spec(slug=slug))

    assert caught.value.code == "invalid_slug"


@pytest.mark.parametrize("target_url", ["", "ftp://ok.example/x", "javascript:alert(1)"])
def test_a_short_link_refuses_a_target_that_is_not_an_http_url(target_url: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.ShortLink(_short_link_spec(target_url=target_url))

    assert caught.value.code == "invalid_target_url"


def test_it_admits_distinct_slugs() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"), _short_link_spec("sale"))))
    assert [str(link.slug) for link in short_links.links] == ["promo", "sale"]


def test_it_refuses_a_duplicate_slug_on_construction() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"), _short_link_spec("promo"))))
    assert caught.value.code == "duplicate_slug"


def test_it_refuses_a_duplicate_slug_on_add() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"),)))
    with pytest.raises(errors.DomainError) as caught:
        short_links.add(_short_link_spec("promo"))
    assert caught.value.code == "duplicate_slug"


def test_it_names_the_index_of_an_invalid_link() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec(), _short_link_spec(slug="BAD SLUG"))))
    assert "index 1" in caught.value.message


def test_it_deactivates_by_slug() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"),)))
    short_links.deactivate(domain.Slug("promo"))
    assert [str(link.status) for link in short_links.links] == ["inactive"]


def test_it_refuses_to_deactivate_a_missing_slug() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=()))
    with pytest.raises(errors.DomainError) as caught:
        short_links.deactivate(domain.Slug("promo"))
    assert caught.value.code == "link_missing"


def test_its_accessor_hands_back_copies() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"),)))
    short_links.links[0].deactivate()
    assert [str(link.status) for link in short_links.links] == ["active"]


def test_it_hands_back_the_target_of_an_active_link() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"),)))
    assert str(short_links.active_target(domain.Slug("promo"))) == "https://ok.example/x"


def test_it_refuses_the_target_of_a_deactivated_link() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"),)))
    short_links.deactivate(domain.Slug("promo"))
    with pytest.raises(errors.DomainError) as caught:
        short_links.active_target(domain.Slug("promo"))
    assert caught.value.code == "link_missing"


def test_it_refuses_the_target_of_a_slug_it_does_not_carry() -> None:
    short_links = domain.ShortLinks(domain.ShortLinksSpec(links=(_short_link_spec("promo"),)))
    with pytest.raises(errors.DomainError) as caught:
        short_links.active_target(domain.Slug("nosuch"))
    assert caught.value.code == "link_missing"
    assert "nosuch" in caught.value.message


def test_campaign_id_round_trips_through_its_canonical_exit() -> None:
    campaign_id = domain.CampaignID("0123456789abcdef")

    assert domain.CampaignID(str(campaign_id)) == campaign_id


def test_campaign_ids_with_the_same_digits_are_the_same_value() -> None:
    a = domain.CampaignID("0123456789abcdef")
    b = domain.CampaignID("0123456789abcdef")

    assert a == b
    assert hash(a) == hash(b)


def test_campaign_ids_with_different_digits_are_different_values() -> None:
    a = domain.CampaignID("0123456789abcdef")
    b = domain.CampaignID("fedcba9876543210")

    assert a != b


@pytest.mark.parametrize(
    "value", ["", "0123456789abcde", "0123456789abcdef0", "0123456789ABCDEF", "0123456789abcdeg"]
)
def test_a_campaign_id_that_is_not_sixteen_lowercase_hex_is_rejected(value: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.CampaignID(value)

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "invalid_campaign_id"


@pytest.mark.parametrize("state", [domain.LinkState.ACTIVE, domain.LinkState.INACTIVE])
def test_a_link_status_round_trips_through_its_canonical_exit(state: domain.LinkState) -> None:
    link_status = domain.LinkStatus(state)

    assert domain.LinkStatus(domain.LinkState(str(link_status))) == link_status


def test_the_two_link_states_are_different_values() -> None:
    active = domain.LinkStatus(domain.LinkState.ACTIVE)
    inactive = domain.LinkStatus(domain.LinkState.INACTIVE)

    assert active != inactive


@pytest.mark.parametrize("value", ["", "ACTIVE", "paused", "Active", " active"])
def test_a_string_outside_the_declared_states_is_not_a_link_state(value: str) -> None:
    with pytest.raises(ValueError):
        domain.LinkState(value)


def test_a_target_url_round_trips_through_its_canonical_exit() -> None:
    target_url = domain.TargetURL("https://ok.example/x?a=1#frag")

    assert domain.TargetURL(str(target_url)) == target_url


def test_target_urls_differing_only_in_path_are_different_values() -> None:
    assert domain.TargetURL("https://ok.example/a") != domain.TargetURL("https://ok.example/b")


def test_a_target_url_carrying_a_control_character_is_rejected() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.TargetURL("https://ok.example/\r\nX-Injected: yes")

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
    with pytest.raises(errors.DomainError) as caught:
        domain.TargetURL(value)

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "invalid_target_url"


def test_the_slug_re_exported_here_round_trips_through_its_canonical_exit() -> None:
    slug = domain.Slug("spring-sale")

    assert domain.Slug(str(slug)) == slug


@pytest.mark.parametrize("value", ["", "Promo", "promo sale", "-promo", "promo-", "promo_sale"])
def test_the_slug_re_exported_here_still_rejects_a_malformed_value(value: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Slug(value)

    assert caught.value.code == "invalid_slug"


def test_a_money_amount_round_trips_through_its_canonical_exit() -> None:
    money_amount = domain.MoneyAmount("1.50")

    assert domain.MoneyAmount(str(money_amount)) == money_amount


def test_a_money_amount_keeps_the_scale_it_was_written_with() -> None:
    assert str(domain.MoneyAmount("1.50")) == "1.50"
    assert str(domain.MoneyAmount("1.5")) == "1.5"


def test_money_amounts_that_are_numerically_equal_are_the_same_value() -> None:
    a = domain.MoneyAmount("1.5")
    b = domain.MoneyAmount("1.50")

    assert a == b
    assert hash(a) == hash(b)


def test_a_money_amount_of_zero_is_admitted() -> None:
    assert domain.MoneyAmount("0") == domain.MoneyAmount("0.00")


@pytest.mark.parametrize("value", ["", "abc", "1.2.3", "1,50", "$1.00", "one"])
def test_a_money_amount_that_is_not_a_number_is_rejected(value: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.MoneyAmount(value)

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "invalid_budget_amount"
    assert "is not a number" in caught.value.message


@pytest.mark.parametrize(
    "value", ["Infinity", "-Infinity", "inf", "-inf", "NaN", "-NaN", "sNaN"]
)
def test_a_money_amount_that_is_not_finite_is_rejected(value: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.MoneyAmount(value)

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "invalid_budget_amount"
    assert "is not a finite number" in caught.value.message


@pytest.mark.parametrize("value", ["NaN", "Infinity"])
def test_a_non_finite_money_amount_never_leaks_a_decimal_error(value: str) -> None:
    with pytest.raises(errors.DomainError):
        domain.MoneyAmount(value)


@pytest.mark.parametrize("value", ["-0.01", "-1", "-1000000"])
def test_a_negative_money_amount_is_rejected(value: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.MoneyAmount(value)

    assert caught.value.code == "invalid_budget_amount"
    assert "must not be negative" in caught.value.message


def test_a_money_currency_round_trips_through_its_canonical_exit() -> None:
    money_currency = domain.MoneyCurrency("USD")

    assert domain.MoneyCurrency(str(money_currency)) == money_currency


def test_different_currency_codes_are_different_values() -> None:
    assert domain.MoneyCurrency("USD") != domain.MoneyCurrency("EUR")


@pytest.mark.parametrize("value", ["", "us", "usd", "USDD", "US1", "US", "U S"])
def test_a_currency_that_is_not_three_uppercase_letters_is_rejected(value: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.MoneyCurrency(value)

    assert caught.value.kind is errors.Kind.VALIDATION
    assert caught.value.code == "invalid_budget_currency"


def test_money_hands_back_its_parts_as_value_objects() -> None:
    money = domain.Money(domain.MoneySpec("100.00", "USD"))

    assert money.amount == domain.MoneyAmount("100.00")
    assert money.currency == domain.MoneyCurrency("USD")


def test_money_with_the_same_parts_is_the_same_value() -> None:
    a = domain.Money(domain.MoneySpec("100.00", "USD"))
    b = domain.Money(domain.MoneySpec("100.00", "USD"))

    assert a == b
    assert hash(a) == hash(b)


def test_money_in_a_different_currency_is_a_different_value() -> None:
    usd = domain.Money(domain.MoneySpec("100.00", "USD"))
    eur = domain.Money(domain.MoneySpec("100.00", "EUR"))

    assert usd != eur


def test_money_propagates_an_amount_rejection() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Money(domain.MoneySpec("nope", "USD"))

    assert caught.value.code == "invalid_budget_amount"


def test_money_propagates_a_currency_rejection() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Money(domain.MoneySpec("100.00", "nope"))

    assert caught.value.code == "invalid_budget_currency"


def test_money_is_immutable_once_constructed() -> None:
    money = domain.Money(domain.MoneySpec("100.00", "USD"))

    with pytest.raises(AttributeError):
        setattr(money, "amount", domain.MoneyAmount("1.00"))


@ts.helper
def _campaign_spec(
    id: str = "0123456789abcdef",
    amount: str = "100.00",
    currency: str = "USD",
    slug: str = "spring-sale",
    target_url: str = "https://ok.example/x",
    active: bool = True,
) -> domain.CampaignSpec:
    return domain.CampaignSpec(
        id=id,
        budget=domain.MoneySpec(amount=amount, currency=currency),
        links=domain.ShortLinksSpec(links=(domain.ShortLinkSpec(slug=slug, target_url=target_url, active=active),)),
    )


def test_a_campaign_carries_every_field_of_its_spec() -> None:
    campaign_spec = _campaign_spec()

    campaign = domain.Campaign(campaign_spec)

    assert campaign.id == domain.CampaignID(campaign_spec.id)
    assert campaign.budget == domain.Money(campaign_spec.budget)
    assert [link.slug for link in campaign.links] == [domain.Slug(campaign_spec.links.links[0].slug)]


def test_a_campaign_may_start_with_no_links() -> None:
    campaign = domain.Campaign(
        domain.CampaignSpec(
            id="0123456789abcdef",
            budget=domain.MoneySpec(amount="100.00", currency="USD"),
            links=domain.ShortLinksSpec(links=()),
        )
    )

    assert campaign.links == ()


def test_the_links_accessor_hands_back_copies_the_caller_cannot_mutate() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo", active=True))

    campaign.links[0].deactivate()

    assert campaign.links[0].status == domain.LinkStatus(domain.LinkState.ACTIVE)


def test_add_short_link_admits_a_new_slug() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))

    campaign.add_short_link(
        domain.ShortLinkSpec(slug="sale", target_url="https://ok.example/y", active=True)
    )

    assert [link.slug for link in campaign.links] == [domain.Slug("promo"), domain.Slug("sale")]


def test_add_short_link_refuses_a_slug_the_campaign_already_carries() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))

    with pytest.raises(errors.DomainError) as caught:
        campaign.add_short_link(
            domain.ShortLinkSpec(slug="promo", target_url="https://ok.example/y", active=True)
        )

    assert caught.value.kind is errors.Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"
    assert len(campaign.links) == 1


def test_add_short_link_refuses_a_malformed_link_and_keeps_the_campaign_intact() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))

    with pytest.raises(errors.DomainError) as caught:
        campaign.add_short_link(
            domain.ShortLinkSpec(slug="BAD SLUG", target_url="https://ok.example/y", active=True)
        )

    assert caught.value.code == "invalid_slug"
    assert len(campaign.links) == 1


def test_construction_refuses_a_duplicate_slug_in_the_spec() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Campaign(
            domain.CampaignSpec(
                id="0123456789abcdef",
                budget=domain.MoneySpec(amount="100.00", currency="USD"),
                links=domain.ShortLinksSpec(links=(
                    domain.ShortLinkSpec(
                        slug="promo", target_url="https://ok.example/a", active=True
                    ),
                    domain.ShortLinkSpec(
                        slug="promo", target_url="https://ok.example/b", active=True
                    ),
                )),
            )
        )

    assert caught.value.kind is errors.Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"


def test_construction_names_the_index_of_the_link_it_refused() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Campaign(
            domain.CampaignSpec(
                id="0123456789abcdef",
                budget=domain.MoneySpec(amount="100.00", currency="USD"),
                links=domain.ShortLinksSpec(links=(
                    domain.ShortLinkSpec(
                        slug="promo", target_url="https://ok.example/a", active=True
                    ),
                    domain.ShortLinkSpec(
                        slug="promo-two", target_url="ftp://bad.example", active=True
                    ),
                )),
            )
        )

    assert caught.value.code == "invalid_short_link"
    assert "index 1" in caught.value.message


def test_construction_propagates_a_budget_rejection() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Campaign(_campaign_spec(currency="dollars"))

    assert caught.value.code == "invalid_budget_currency"


def test_construction_propagates_an_id_rejection() -> None:
    with pytest.raises(errors.DomainError) as caught:
        domain.Campaign(_campaign_spec(id="not-an-id"))

    assert caught.value.code == "invalid_campaign_id"


def test_deactivate_short_link_flips_only_the_named_link() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))
    campaign.add_short_link(
        domain.ShortLinkSpec(slug="sale", target_url="https://ok.example/y", active=True)
    )

    campaign.deactivate_short_link(domain.Slug("promo"))

    assert [link.status for link in campaign.links] == [
        domain.LinkStatus(domain.LinkState.INACTIVE),
        domain.LinkStatus(domain.LinkState.ACTIVE),
    ]


def test_deactivate_short_link_refuses_a_slug_the_campaign_does_not_carry() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))

    with pytest.raises(errors.DomainError) as caught:
        campaign.deactivate_short_link(domain.Slug("nosuch"))

    assert caught.value.kind is errors.Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_active_target_hands_back_the_url_of_the_named_active_link() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))

    assert str(campaign.active_target(domain.Slug("promo"))) == "https://ok.example/x"


def test_active_target_refuses_a_link_that_was_deactivated() -> None:
    campaign = domain.Campaign(_campaign_spec(slug="promo"))
    campaign.deactivate_short_link(domain.Slug("promo"))

    with pytest.raises(errors.DomainError) as caught:
        campaign.active_target(domain.Slug("promo"))

    assert caught.value.kind is errors.Kind.NOT_FOUND
    assert caught.value.code == "link_missing"
