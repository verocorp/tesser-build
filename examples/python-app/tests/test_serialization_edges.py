from __future__ import annotations

import ast
import pathlib

import pytest
import tesser.testing as ts

from campaign.adapters.gateways.repo_memory import InMemoryCampaignRepository
from campaign.adapters.handlers.http import Handler
from campaign.application.parts import CampaignParts, CheckOutcome, MoneyParts, campaign_parts
from campaign.application.service import CampaignService, TargetChecker
from campaign.application.views import required_campaign
from campaign.domain.campaign import Campaign, CampaignSpec
from campaign.domain.money import MoneySpec
from campaign.domain.short_link import ShortLinkSpec
from errors import DomainError
from protocol.http import HttpRequest
from tests.support import parts_tuple




@ts.helper  # tesser-category: spec
def campaign_spec(slug: str = "promo") -> CampaignSpec:
    return CampaignSpec(
        id="0123456789abcdef",
        budget=MoneySpec(amount="100.00", currency="USD"),
        links=(ShortLinkSpec(slug=slug, target_url="https://ok.example/x", active=True),),
    )


@ts.fake
class _AllowAll(TargetChecker):
    def check(self, target_url: str) -> CheckOutcome:
        return CheckOutcome(True, "ok")


def test_row_golden_locks_the_storage_shape() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(campaign_parts(Campaign(campaign_spec())))
    assert parts_tuple(repo._rows["0123456789abcdef"]) == (
        "0123456789abcdef",
        "100.00",
        "USD",
        (("promo", "https://ok.example/x", True),),
    )


def test_wire_golden_locks_the_campaign_payload() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(campaign_parts(Campaign(campaign_spec())))
    handler = Handler(CampaignService(repo, _AllowAll()))
    resp = handler.get_campaign(HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b""))
    assert resp.status_code == 200
    assert resp.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "active": True}],
    }


def test_wire_golden_locks_resolve_as_a_real_redirect() -> None:
    repo = InMemoryCampaignRepository()
    repo.save(campaign_parts(Campaign(campaign_spec())))
    handler = Handler(CampaignService(repo, _AllowAll()))
    resp = handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))
    assert resp.status_code == 302
    assert resp.body == b""
    assert resp.headers == {"Location": "https://ok.example/x"}


def test_load_reconstructs_value_equal_non_identical() -> None:
    repo = InMemoryCampaignRepository()
    original = Campaign(campaign_spec())
    repo.save(campaign_parts(original))
    loaded = required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
    assert loaded is not original
    assert parts_tuple(campaign_parts(loaded)) == parts_tuple(campaign_parts(original))


def test_store_holds_rows_not_live_objects() -> None:
    repo = InMemoryCampaignRepository()
    original = Campaign(campaign_spec())
    repo.save(campaign_parts(original))
    loaded = required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
    loaded.add_short_link(ShortLinkSpec(slug="extra", target_url="https://ok.example/e", active=True))
    reloaded = required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
    assert parts_tuple(campaign_parts(reloaded)) == parts_tuple(campaign_parts(original))


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
    repo.save(campaign_parts(Campaign(campaign_spec())))
    row = repo._rows["0123456789abcdef"]
    stale = CampaignParts(
        id=row.id,
        budget=MoneyParts(amount="-5", currency=row.budget.currency),
        links=row.links,
    )
    repo._rows["0123456789abcdef"] = stale
    with pytest.raises(DomainError):
        required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
