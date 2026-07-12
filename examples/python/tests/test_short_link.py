import pytest

from campaign.short_link import ShortLink, ShortLinkSpec
from campaign.slug import Slug


def _spec(slug: str = "spring-sale", active: bool = True) -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url="https://a.example", active=active)


class TestShortLink:
    def test_from_spec_builds_children(self) -> None:
        link = ShortLink.from_spec(_spec())
        assert link.slug == Slug("spring-sale")
        assert str(link.target_url) == "https://a.example"
        assert link.active is True

    def test_from_spec_wraps_child_error(self) -> None:
        with pytest.raises(ValueError, match="invalid slug"):
            ShortLink.from_spec(_spec(slug="X"))

    def test_equality_is_identity_by_slug(self) -> None:
        # Same slug -> same link, even if other attributes differ; different
        # slug -> different link.
        a = ShortLink.from_spec(_spec(slug="spring-sale", active=True))
        b = ShortLink.from_spec(_spec(slug="spring-sale", active=False))
        c = ShortLink.from_spec(_spec(slug="autumn-sale"))
        assert a == b
        assert hash(a) == hash(b)
        assert a != c

    def test_deactivate_is_guarded(self) -> None:
        link = ShortLink.from_spec(_spec())
        link.deactivate()
        assert link.active is False
        # A link can only be deactivated once.
        with pytest.raises(ValueError, match="already deactivated"):
            link.deactivate()
