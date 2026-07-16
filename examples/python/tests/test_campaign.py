import pytest

from campaign.campaign import (
    MAX_SHORT_LINKS_PER_CAMPAIGN,
    Campaign,
    CampaignSpec,
)
from campaign.short_link import ShortLinkSpec
from campaign.slug import Slug


def _link(slug: str) -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url="https://a.example", active=True)


def _spec(*slugs: str) -> CampaignSpec:
    return CampaignSpec(
        id="c1", name="Spring", links=tuple(_link(s) for s in slugs)
    )


class TestCampaignInvariants:
    def test_constructs_with_empty_links(self) -> None:
        c = Campaign(_spec())
        assert c.links == ()

    def test_rejects_duplicate_slug_at_construction(self) -> None:
        with pytest.raises(ValueError, match="duplicate slug"):
            Campaign(_spec("spring-sale", "spring-sale"))

    def test_rejects_over_max_links_at_construction(self) -> None:
        slugs = [f"link-{i:04d}" for i in range(MAX_SHORT_LINKS_PER_CAMPAIGN + 1)]
        with pytest.raises(ValueError, match="maximum"):
            Campaign(_spec(*slugs))


class TestCampaignTransitions:
    def test_add_short_link_enforces_unique_slug(self) -> None:
        c = Campaign(_spec("spring-sale"))
        with pytest.raises(ValueError, match="duplicate slug"):
            c.add_short_link(_link("spring-sale"))

    def test_add_short_link_enforces_max(self) -> None:
        slugs = [f"link-{i:04d}" for i in range(MAX_SHORT_LINKS_PER_CAMPAIGN)]
        c = Campaign(_spec(*slugs))
        with pytest.raises(ValueError, match="maximum"):
            c.add_short_link(_link("one-too-many"))

    def test_deactivate_short_link_via_root(self) -> None:
        c = Campaign(_spec("spring-sale"))
        c.deactivate_short_link(Slug("spring-sale"))
        assert c.links[0].active is False

    def test_deactivate_unknown_slug_raises(self) -> None:
        c = Campaign(_spec("spring-sale"))
        with pytest.raises(ValueError, match="no short link with slug"):
            c.deactivate_short_link(Slug("autumn-sale"))


def test_links_accessor_is_a_defensive_copy() -> None:
    c = Campaign(_spec("spring-sale"))
    links = c.links
    assert isinstance(links, tuple)  # callers can't mutate the root's collection
    # Mutating the returned children does not change the campaign's own count.
    c.add_short_link(_link("autumn-sale"))
    assert len(links) == 1
    assert len(c.links) == 2


def test_links_accessor_does_not_leak_mutable_children() -> None:
    # The container is copied AND so are the mutable child entities: calling a
    # mutating method on a returned link must not reach the aggregate's own
    # state. Deactivation only happens through the root's guarded transition.
    c = Campaign(_spec("spring-sale"))
    c.links[0].deactivate()  # try to mutate a returned child directly
    assert c.links[0].active is True  # the aggregate's own state is untouched


def test_aggregates_are_not_value_compared() -> None:
    # Comparing aggregates by value is a bug; __eq__ = None makes it raise.
    a = Campaign(_spec("spring-sale"))
    b = Campaign(_spec("spring-sale"))
    with pytest.raises(TypeError):
        # mypy also rejects this statically ("None not callable"), so the ignore
        # documents that the comparison is deliberately exercised for its raise.
        _ = a == b  # type: ignore[misc]
    with pytest.raises(TypeError):
        hash(a)  # and unhashable, so it can't be a dict key / set member
