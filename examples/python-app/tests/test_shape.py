from __future__ import annotations

import dataclasses
import json
import pathlib

import campaign
import linkpolicy
import reports
from campaign.adapters.handlers.http import Handler
from campaign.client import LinkView, ResolveResponse
from campaign.wiring.config import Config as CampaignConfig
from campaign.wiring.wire import build as build_campaign
from reports.client import LinkVerdictView
from tests.discovery import discovered_contexts

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_required_roles_present_per_context() -> None:
    for ctx in discovered_contexts():
        for role in ("domain", "application", "wiring"):
            assert (ROOT / ctx / role).is_dir(), f"{ctx}/{role} missing"
    for ctx in ("campaign", "linkpolicy"):
        assert (ROOT / ctx / "adapters").is_dir(), f"{ctx}/adapters missing"


def test_public_seam_is_client_plus_dtos_at_top_level() -> None:
    assert hasattr(campaign, "Client")
    assert hasattr(linkpolicy, "Client")
    assert hasattr(reports, "Client")
    assert dataclasses.is_dataclass(ResolveResponse)
    for field in dataclasses.fields(ResolveResponse):
        assert field.type in ("str", str), field
    assert dataclasses.is_dataclass(LinkView)
    for field in dataclasses.fields(LinkView):
        assert field.type in ("str", str, "bool", bool), field
    assert dataclasses.is_dataclass(LinkVerdictView)
    for field in dataclasses.fields(LinkVerdictView):
        assert field.type in ("str", str, "bool", bool), field


def test_config_lives_in_wiring_not_on_public_top_level() -> None:
    for ctx in discovered_contexts():
        assert (ROOT / ctx / "wiring" / "config.py").is_file()
        assert not (ROOT / ctx / "config.py").exists(), f"{ctx} config leaked to the public top level"


class _AllowAllChecker:
    def check(self, target_url: str) -> campaign.CheckOutcome:
        return campaign.CheckOutcome(True, "ok")


def test_handler_translates_wire_to_client_dtos() -> None:
    client, _ = build_campaign(CampaignConfig("memory"), _AllowAllChecker())
    handler = Handler(client)
    created = handler.create_campaign('{"budget": {"amount": "100.00", "currency": "USD"}}')
    assert created.status == 201
    campaign_id = created.body["campaign_id"]
    assert created.body == {
        "campaign_id": campaign_id,
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [],
    }
    added = handler.add_link(
        json.dumps({"campaign_id": campaign_id, "slug": "promo", "target_url": "https://ok.example/x"})
    )
    assert added.status == 200
    assert added.body == {
        "campaign_id": campaign_id,
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "active": True}],
    }
