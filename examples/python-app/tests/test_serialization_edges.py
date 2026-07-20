from __future__ import annotations

import ast
import dataclasses
import pathlib

import pytest

from campaign.adapters.gateways.repo_memory import InMemoryCampaignRepository
from campaign.adapters.handlers.http import Handler
from campaign.application.parts import campaign_parts
from campaign.application.service import CampaignService
from campaign.client import CheckOutcome
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from campaign.domain.values import CampaignID
from errors import DomainError

_CAMPAIGN_ID = "0123456789abcdef"


def _campaign() -> Campaign:
    return Campaign(
        CampaignSpec(
            id=_CAMPAIGN_ID,
            budget=MoneySpec(amount="100.00", currency="USD"),
            links=(ShortLinkSpec(slug="promo", target_url="https://ok.example/x", active=True),),
        )
    )


class _AllowAll:
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


def test_row_golden_locks_the_storage_shape() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(_campaign())
    assert dataclasses.asdict(repo._rows[_CAMPAIGN_ID]) == {
        "campaign_id": _CAMPAIGN_ID,
        "budget_amount": "100.00",
        "budget_currency": "USD",
        "links": ({"slug": "promo", "target_url": "https://ok.example/x", "active": True},),
    }


def test_wire_golden_locks_the_campaign_payload() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(_campaign())
    handler = Handler(CampaignService(repo, _AllowAll()))
    resp = handler.get_campaign(_CAMPAIGN_ID)
    assert resp.status == 200
    assert resp.body == {
        "campaign_id": _CAMPAIGN_ID,
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "active": True}],
    }


def test_wire_golden_locks_the_resolve_payload() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(_campaign())
    handler = Handler(CampaignService(repo, _AllowAll()))
    resp = handler.resolve("promo")
    assert resp.status == 302
    assert resp.body == {"location": "https://ok.example/x"}


def test_load_reconstructs_value_equal_non_identical() -> None:
    repo = InMemoryCampaignRepository()
    original = _campaign()
    repo.save(original)
    loaded = repo.find(CampaignID(_CAMPAIGN_ID))
    assert loaded is not None
    assert loaded is not original
    assert campaign_parts(loaded) == campaign_parts(original)


def test_store_holds_rows_not_live_objects() -> None:
    repo = InMemoryCampaignRepository()
    original = _campaign()
    repo.save(original)
    loaded = repo.find(CampaignID(_CAMPAIGN_ID))
    assert loaded is not None
    loaded.add_short_link(ShortLinkSpec(slug="extra", target_url="https://ok.example/e", active=True))
    reloaded = repo.find(CampaignID(_CAMPAIGN_ID))
    assert reloaded is not None
    assert campaign_parts(reloaded) == campaign_parts(original)


def test_parts_module_never_touches_specs() -> None:
    source = (
        pathlib.Path(__file__).resolve().parent.parent
        / "campaign"
        / "application"
        / "parts.py"
    ).read_text(encoding="utf-8")
    imported = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    referenced = {
        node.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Name)
    }
    spec_touches = {name for name in imported | referenced if name.endswith("Spec")}
    assert not spec_touches, f"parts is outbound-only; it must never touch specs: {spec_touches}"


def test_load_reruns_invariants_on_stale_rows() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(_campaign())
    row = repo._rows[_CAMPAIGN_ID]
    repo._rows[_CAMPAIGN_ID] = dataclasses.replace(row, budget_amount="-5")
    with pytest.raises(DomainError):
        repo.find(CampaignID(_CAMPAIGN_ID))
