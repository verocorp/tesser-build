import pytest

from campaign.short_link import ShortLink, ShortLinkSpec
from campaign.slug import Slug


def _spec(slug: str = "spring-sale", active: bool = True) -> ShortLinkSpec:
    return ShortLinkSpec(slug=slug, target_url="https://a.example", active=active)


class TestShortLink:
    def test_constructor_builds_children(self) -> None:
        link = ShortLink(_spec())
        assert link.slug == Slug("spring-sale")
        assert str(link.target_url) == "https://a.example"
        assert link.active is True

    def test_constructor_wraps_child_error(self) -> None:
        with pytest.raises(ValueError, match="invalid slug"):
            ShortLink(_spec(slug="X"))

    def test_equality_is_identity_by_slug(self) -> None:
        # Same slug -> same link, even if other attributes differ; different
        # slug -> different link.
        a = ShortLink(_spec(slug="spring-sale", active=True))
        b = ShortLink(_spec(slug="spring-sale", active=False))
        c = ShortLink(_spec(slug="autumn-sale"))
        assert a == b
        assert hash(a) == hash(b)
        assert a != c

    def test_deactivate_is_guarded(self) -> None:
        link = ShortLink(_spec())
        link.deactivate()
        assert link.active is False
        # A link can only be deactivated once.
        with pytest.raises(ValueError, match="already deactivated"):
            link.deactivate()
