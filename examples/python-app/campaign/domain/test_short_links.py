from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
import kernel.slug as kernel_slug
import tesser.errors as errors


@ts.helper
def _spec(
    slug: str = "promo", target_url: str = "https://ok.example/x", active: bool = True
) -> short_link.ShortLinkSpec:
    return short_link.ShortLinkSpec(slug=slug, target_url=target_url, active=active)


def test_it_admits_distinct_slugs() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"), _spec("sale"))))
    assert [str(link.slug) for link in links.links] == ["promo", "sale"]


def test_it_refuses_a_duplicate_slug_on_construction() -> None:
    with pytest.raises(errors.DomainError) as caught:
        short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"), _spec("promo"))))
    assert caught.value.code == "duplicate_slug"


def test_it_refuses_a_duplicate_slug_on_add() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"),)))
    with pytest.raises(errors.DomainError) as caught:
        links.add(_spec("promo"))
    assert caught.value.code == "duplicate_slug"


def test_it_names_the_index_of_an_invalid_link() -> None:
    with pytest.raises(errors.DomainError) as caught:
        short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec(), _spec(slug="BAD SLUG"))))
    assert "index 1" in caught.value.message


def test_it_deactivates_by_slug() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"),)))
    links.deactivate(kernel_slug.Slug("promo"))
    assert [str(link.status) for link in links.links] == ["inactive"]


def test_it_refuses_to_deactivate_a_missing_slug() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=()))
    with pytest.raises(errors.DomainError) as caught:
        links.deactivate(kernel_slug.Slug("promo"))
    assert caught.value.code == "link_missing"


def test_its_accessor_hands_back_copies() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"),)))
    links.links[0].deactivate()
    assert [str(link.status) for link in links.links] == ["active"]


def test_it_hands_back_the_target_of_an_active_link() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"),)))
    assert str(links.active_target(kernel_slug.Slug("promo"))) == "https://ok.example/x"


def test_it_refuses_the_target_of_a_deactivated_link() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"),)))
    links.deactivate(kernel_slug.Slug("promo"))
    with pytest.raises(errors.DomainError) as caught:
        links.active_target(kernel_slug.Slug("promo"))
    assert caught.value.code == "link_missing"


def test_it_refuses_the_target_of_a_slug_it_does_not_carry() -> None:
    links = short_links.ShortLinks(short_links.ShortLinksSpec(links=(_spec("promo"),)))
    with pytest.raises(errors.DomainError) as caught:
        links.active_target(kernel_slug.Slug("nosuch"))
    assert caught.value.code == "link_missing"
    assert "nosuch" in caught.value.message
