from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.domain.short_link as short_link
import campaign.domain.values as values
import kernel.slug as kernel_slug
import tesser.errors as errors


@ts.helper
def _spec(
    slug: str = "spring-sale",
    target_url: str = "https://ok.example/x",
    active: bool = True,
) -> short_link.ShortLinkSpec:
    return short_link.ShortLinkSpec(slug=slug, target_url=target_url, active=active)


def test_a_short_link_carries_every_field_of_its_spec() -> None:
    spec = _spec()

    link = short_link.ShortLink(spec)

    assert link.slug == kernel_slug.Slug(spec.slug)
    assert link.target_url == values.TargetURL(spec.target_url)
    assert link.status == values.LinkStatus(values.LinkState.ACTIVE)


def test_a_short_link_built_inactive_starts_inactive() -> None:
    link = short_link.ShortLink(_spec(active=False))

    assert link.status == values.LinkStatus(values.LinkState.INACTIVE)


def test_deactivate_turns_an_active_link_inactive() -> None:
    link = short_link.ShortLink(_spec(active=True))

    link.deactivate()

    assert link.status == values.LinkStatus(values.LinkState.INACTIVE)


def test_deactivate_leaves_an_already_inactive_link_inactive() -> None:
    link = short_link.ShortLink(_spec(active=False))

    link.deactivate()

    assert link.status == values.LinkStatus(values.LinkState.INACTIVE)


def test_deactivate_leaves_the_slug_and_target_untouched() -> None:
    link = short_link.ShortLink(_spec(slug="promo", target_url="https://ok.example/a"))

    link.deactivate()

    assert link.slug == kernel_slug.Slug("promo")
    assert link.target_url == values.TargetURL("https://ok.example/a")


def test_a_short_link_is_identified_by_its_slug() -> None:
    link = short_link.ShortLink(_spec(slug="promo"))

    assert link.identity == kernel_slug.Slug("promo")


def test_two_short_links_with_the_same_slug_are_the_same_entity() -> None:
    a = short_link.ShortLink(_spec(slug="promo", target_url="https://ok.example/a"))
    b = short_link.ShortLink(_spec(slug="promo", target_url="https://ok.example/b", active=False))

    assert a == b
    assert hash(a) == hash(b)


def test_two_short_links_with_different_slugs_are_different_entities() -> None:
    a = short_link.ShortLink(_spec(slug="promo"))
    b = short_link.ShortLink(_spec(slug="sale"))

    assert a != b


@pytest.mark.parametrize("slug", ["", "Promo", "promo sale", "-promo"])
def test_a_short_link_refuses_a_malformed_slug(slug: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        short_link.ShortLink(_spec(slug=slug))

    assert caught.value.code == "invalid_slug"


@pytest.mark.parametrize("target_url", ["", "ftp://ok.example/x", "javascript:alert(1)"])
def test_a_short_link_refuses_a_target_that_is_not_an_http_url(target_url: str) -> None:
    with pytest.raises(errors.DomainError) as caught:
        short_link.ShortLink(_spec(target_url=target_url))

    assert caught.value.code == "invalid_target_url"
