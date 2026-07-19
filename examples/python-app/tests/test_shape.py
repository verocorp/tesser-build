from __future__ import annotations

import dataclasses
import pathlib

import campaign
import linkpolicy
import reports
from campaign.adapters.handlers.http import Handler
from campaign.client import CreateLinkResponse
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
    assert dataclasses.is_dataclass(CreateLinkResponse)
    for field in dataclasses.fields(CreateLinkResponse):
        assert field.type in ("str", str), field
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
    resp = handler.create_link('{"slug": "promo", "target_url": "https://ok.example/x"}')
    assert resp.status == 201
    assert resp.body == {"slug": "promo", "target_url": "https://ok.example/x"}
