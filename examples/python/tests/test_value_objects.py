import pytest

from campaign.campaign_id import CampaignID
from campaign.campaign_name import CampaignName
from campaign.slug import Slug
from campaign.target_url import TargetURL


class TestSlug:
    def test_equality(self) -> None:
        # A slug has one representation; equal values are equal, and hash
        # agrees so slugs work as dict keys / set members.
        assert Slug("spring-sale") == Slug("spring-sale")
        assert hash(Slug("spring-sale")) == hash(Slug("spring-sale"))
        assert Slug("spring-sale") != Slug("autumn-sale")

    @pytest.mark.parametrize("bad", ["", "ab", "a" * 21, "Spring", "spring_sale", "a b"])
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError, match="invalid slug"):
            Slug(bad)

    def test_str_is_display(self) -> None:
        assert str(Slug("spring-sale")) == "spring-sale"


class TestTargetURL:
    def test_equality(self) -> None:
        assert TargetURL("https://a.example") == TargetURL("https://a.example")
        assert TargetURL("https://a.example") != TargetURL("https://b.example")

    @pytest.mark.parametrize("bad", ["", "example.com", "ftp://x", "  https://x"])
    def test_rejects_non_http(self, bad: str) -> None:
        with pytest.raises(ValueError, match="must start with"):
            TargetURL(bad)

    def test_str_is_display(self) -> None:
        assert str(TargetURL("https://a.example")) == "https://a.example"


class TestCampaignID:
    def test_equality(self) -> None:
        assert CampaignID("c1") == CampaignID("c1")
        assert CampaignID("c1") != CampaignID("c2")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            CampaignID("")


class TestCampaignName:
    def test_equality(self) -> None:
        assert CampaignName("Spring") == CampaignName("Spring")

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_rejects_blank(self, bad: str) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            CampaignName(bad)


def test_value_objects_are_immutable() -> None:
    # frozen=True: assignment raises. Behavior never mutates a value object.
    from dataclasses import FrozenInstanceError

    s = Slug("spring-sale")
    with pytest.raises(FrozenInstanceError):
        s._value = "autumn-sale"  # type: ignore[misc]
