from __future__ import annotations

import pytest

import campaign.domain.money as money
import campaign.domain.values as values
from tesser.errors import DomainError


def test_slug_roundtrip() -> None:
    s = values.Slug("promo")
    assert values.Slug(str(s)) == s


def test_target_url_roundtrip() -> None:
    t = values.TargetURL("https://ok.example/x")
    assert values.TargetURL(str(t)) == t


def test_target_url_rejects_control_characters() -> None:
    with pytest.raises(DomainError):
        values.TargetURL("https://ok.example/\r\nX-Injected: yes")


def test_campaign_id_roundtrip() -> None:
    id = values.CampaignID("0123456789abcdef")
    assert values.CampaignID(str(id)) == id


def test_money_amount_roundtrip() -> None:
    a = money.MoneyAmount("1.50")
    assert money.MoneyAmount(str(a)) == a


def test_money_currency_roundtrip() -> None:
    c = money.MoneyCurrency("USD")
    assert money.MoneyCurrency(str(c)) == c
