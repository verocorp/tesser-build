from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
import campaign.domain.values as values
import kernel.slug as kernel_slug
import tesser.errors as errors


@ts.helper
def _campaign_spec(
    id: str = "0123456789abcdef",
    amount: str = "100.00",
    currency: str = "USD",
    slug: str = "spring-sale",
    target_url: str = "https://ok.example/x",
    active: bool = True,
) -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id=id,
        budget=money.MoneySpec(amount=amount, currency=currency),
        links=short_links.ShortLinksSpec(links=(short_link.ShortLinkSpec(slug=slug, target_url=target_url, active=active),)),
    )


def test_a_campaign_carries_every_field_of_its_spec() -> None:
    spec = _campaign_spec()

    c = campaign.Campaign(spec)

    assert c.id == values.CampaignID(spec.id)
    assert c.budget == money.Money(spec.budget.amount, spec.budget.currency)
    assert [link.slug for link in c.links] == [kernel_slug.Slug(spec.links.links[0].slug)]


def test_a_campaign_may_start_with_no_links() -> None:
    c = campaign.Campaign(
        campaign.CampaignSpec(
            id="0123456789abcdef",
            budget=money.MoneySpec(amount="100.00", currency="USD"),
            links=short_links.ShortLinksSpec(links=()),
        )
    )

    assert c.links == ()


def test_the_links_accessor_hands_back_copies_the_caller_cannot_mutate() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo", active=True))

    c.links[0].deactivate()

    assert c.links[0].status == values.LinkStatus(values.LinkState.ACTIVE)


def test_add_short_link_admits_a_new_slug() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))

    c.add_short_link(
        short_link.ShortLinkSpec(slug="sale", target_url="https://ok.example/y", active=True)
    )

    assert [link.slug for link in c.links] == [kernel_slug.Slug("promo"), kernel_slug.Slug("sale")]


def test_add_short_link_refuses_a_slug_the_campaign_already_carries() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))

    with pytest.raises(errors.DomainError) as caught:
        c.add_short_link(
            short_link.ShortLinkSpec(slug="promo", target_url="https://ok.example/y", active=True)
        )

    assert caught.value.kind is errors.Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"
    assert len(c.links) == 1


def test_add_short_link_refuses_a_malformed_link_and_keeps_the_campaign_intact() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))

    with pytest.raises(errors.DomainError) as caught:
        c.add_short_link(
            short_link.ShortLinkSpec(slug="BAD SLUG", target_url="https://ok.example/y", active=True)
        )

    assert caught.value.code == "invalid_slug"
    assert len(c.links) == 1


def test_construction_refuses_a_duplicate_slug_in_the_spec() -> None:
    with pytest.raises(errors.DomainError) as caught:
        campaign.Campaign(
            campaign.CampaignSpec(
                id="0123456789abcdef",
                budget=money.MoneySpec(amount="100.00", currency="USD"),
                links=short_links.ShortLinksSpec(links=(
                    short_link.ShortLinkSpec(
                        slug="promo", target_url="https://ok.example/a", active=True
                    ),
                    short_link.ShortLinkSpec(
                        slug="promo", target_url="https://ok.example/b", active=True
                    ),
                )),
            )
        )

    assert caught.value.kind is errors.Kind.CONFLICT
    assert caught.value.code == "duplicate_slug"


def test_construction_names_the_index_of_the_link_it_refused() -> None:
    with pytest.raises(errors.DomainError) as caught:
        campaign.Campaign(
            campaign.CampaignSpec(
                id="0123456789abcdef",
                budget=money.MoneySpec(amount="100.00", currency="USD"),
                links=short_links.ShortLinksSpec(links=(
                    short_link.ShortLinkSpec(
                        slug="promo", target_url="https://ok.example/a", active=True
                    ),
                    short_link.ShortLinkSpec(
                        slug="promo-two", target_url="ftp://bad.example", active=True
                    ),
                )),
            )
        )

    assert caught.value.code == "invalid_short_link"
    assert "index 1" in caught.value.message


def test_construction_propagates_a_budget_rejection() -> None:
    with pytest.raises(errors.DomainError) as caught:
        campaign.Campaign(_campaign_spec(currency="dollars"))

    assert caught.value.code == "invalid_budget_currency"


def test_construction_propagates_an_id_rejection() -> None:
    with pytest.raises(errors.DomainError) as caught:
        campaign.Campaign(_campaign_spec(id="not-an-id"))

    assert caught.value.code == "invalid_campaign_id"


def test_deactivate_short_link_flips_only_the_named_link() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))
    c.add_short_link(
        short_link.ShortLinkSpec(slug="sale", target_url="https://ok.example/y", active=True)
    )

    c.deactivate_short_link(kernel_slug.Slug("promo"))

    assert [link.status for link in c.links] == [
        values.LinkStatus(values.LinkState.INACTIVE),
        values.LinkStatus(values.LinkState.ACTIVE),
    ]


def test_deactivate_short_link_refuses_a_slug_the_campaign_does_not_carry() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))

    with pytest.raises(errors.DomainError) as caught:
        c.deactivate_short_link(kernel_slug.Slug("nosuch"))

    assert caught.value.kind is errors.Kind.NOT_FOUND
    assert caught.value.code == "link_missing"


def test_active_target_hands_back_the_url_of_the_named_active_link() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))

    assert str(c.active_target(kernel_slug.Slug("promo"))) == "https://ok.example/x"


def test_active_target_refuses_a_link_that_was_deactivated() -> None:
    c = campaign.Campaign(_campaign_spec(slug="promo"))
    c.deactivate_short_link(kernel_slug.Slug("promo"))

    with pytest.raises(errors.DomainError) as caught:
        c.active_target(kernel_slug.Slug("promo"))

    assert caught.value.kind is errors.Kind.NOT_FOUND
    assert caught.value.code == "link_missing"
