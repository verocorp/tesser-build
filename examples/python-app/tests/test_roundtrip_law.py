from __future__ import annotations

from campaign.domain.money import MoneyAmount, MoneyCurrency
from campaign.domain.values import CampaignID, Slug, TargetURL


def test_slug_roundtrip() -> None:
    s = Slug("promo")
    assert Slug(str(s)) == s


def test_target_url_roundtrip() -> None:
    t = TargetURL("https://ok.example/x")
    assert TargetURL(str(t)) == t


def test_campaign_id_roundtrip() -> None:
    id = CampaignID("0123456789abcdef")
    assert CampaignID(str(id)) == id


def test_money_amount_roundtrip() -> None:
    a = MoneyAmount("1.50")
    assert MoneyAmount(str(a)) == a


def test_money_currency_roundtrip() -> None:
    c = MoneyCurrency("USD")
    assert MoneyCurrency(str(c)) == c
