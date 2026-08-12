from __future__ import annotations

import ast
import pathlib

import pytest
import tesser.testing as ts

import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.adapters.handlers.http as http
import campaign.application.parts as parts
import campaign.application.service as service
import campaign.application.views as views
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
from errors import DomainError
from protocol.http import HttpRequest
def parts_tuple(campaign_parts: parts.CampaignParts) -> tuple[object, ...]:  # tessercheck:ignore TB071
    return (
        campaign_parts.id,
        campaign_parts.budget.amount,
        campaign_parts.budget.currency,
        tuple((link.slug, link.target_url, link.active) for link in campaign_parts.links),
    )




@ts.helper
def campaign_spec(slug: str = "promo") -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="100.00", currency="USD"),
        links=(short_link.ShortLinkSpec(slug=slug, target_url="https://ok.example/x", active=True),),
    )


@ts.fake
class FakeTargetPolicyAllowAll(service.TargetPolicy):
    def check(self, target_url: str) -> parts.PolicyOutcome:
        return parts.PolicyOutcome(True, "ok")


def test_row_golden_locks_the_storage_shape() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(parts.campaign_parts(campaign.Campaign(campaign_spec())))
    assert parts_tuple(repo._rows["0123456789abcdef"]) == (
        "0123456789abcdef",
        "100.00",
        "USD",
        (("promo", "https://ok.example/x", True),),
    )


def test_wire_golden_locks_the_campaign_payload() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(parts.campaign_parts(campaign.Campaign(campaign_spec())))
    handler = http.Handler(service.CampaignService(repo, FakeTargetPolicyAllowAll()))
    resp = handler.get_campaign(HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b""))
    assert resp.status_code == 200
    assert resp.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "active": True}],
    }


def test_wire_golden_locks_resolve_as_a_real_redirect() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(parts.campaign_parts(campaign.Campaign(campaign_spec())))
    handler = http.Handler(service.CampaignService(repo, FakeTargetPolicyAllowAll()))
    resp = handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))
    assert resp.status_code == 302
    assert resp.body == b""
    assert resp.headers == {"Location": "https://ok.example/x"}


def test_load_reconstructs_value_equal_non_identical() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    original = campaign.Campaign(campaign_spec())
    repo.save(parts.campaign_parts(original))
    loaded = views.required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
    assert loaded is not original
    assert parts_tuple(parts.campaign_parts(loaded)) == parts_tuple(parts.campaign_parts(original))


def test_store_holds_rows_not_live_objects() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    original = campaign.Campaign(campaign_spec())
    repo.save(parts.campaign_parts(original))
    loaded = views.required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
    loaded.add_short_link(short_link.ShortLinkSpec(slug="extra", target_url="https://ok.example/e", active=True))
    reloaded = views.required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
    assert parts_tuple(parts.campaign_parts(reloaded)) == parts_tuple(parts.campaign_parts(original))


def test_parts_module_never_touches_specs() -> None:
    source = (
        pathlib.Path(__file__).resolve().parent.parent
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
    attributes = {
        node.attr
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute)
    }
    spec_touches = {
        name for name in imported | referenced | attributes if name.endswith("Spec")
    }
    assert not spec_touches, f"parts is outbound-only; it must never touch specs: {spec_touches}"


def test_load_reruns_invariants_on_stale_rows() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(parts.campaign_parts(campaign.Campaign(campaign_spec())))
    row = repo._rows["0123456789abcdef"]
    stale = parts.CampaignParts(
        id=row.id,
        budget=parts.MoneyParts(amount="-5", currency=row.budget.currency),
        links=row.links,
    )
    repo._rows["0123456789abcdef"] = stale
    with pytest.raises(DomainError):
        views.required_campaign(repo.find("0123456789abcdef"), "0123456789abcdef")
