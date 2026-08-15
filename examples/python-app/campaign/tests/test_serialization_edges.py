from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.adapters.handlers.http as http
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.application.views as views
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
from errors import DomainError
from protocol.http import HttpRequest


def _shape(  # tessercheck:ignore TB071
    id_: str, budget: campaign_repository.MoneyRecord, links: tuple[campaign_repository.LinkRecord, ...]
) -> tuple[object, ...]:
    return (
        id_,
        budget.amount,
        budget.currency,
        tuple((link.slug, link.target_url, link.status) for link in links),
    )


def record_tuple(record: campaign_repository.CampaignRecord) -> tuple[object, ...]:  # tessercheck:ignore TB071
    return _shape(record.id, record.budget, record.links)


def request_tuple(request: campaign_repository.SaveCampaignRequest) -> tuple[object, ...]:  # tessercheck:ignore TB071
    return _shape(request.id, request.budget, request.links)


@ts.helper
def campaign_spec(slug: str = "promo") -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="100.00", currency="USD"),
        links=(short_link.ShortLinkSpec(slug=slug, target_url="https://ok.example/x", active=True),),
    )


@ts.fake
class FakeTargetPolicyAllowAll(target_policy.TargetPolicy):
    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(verdict=target_policy.PolicyVerdict.ALLOWED, reason="ok")


def _find(  # tessercheck:ignore TB071
    repo: repo_memory.InMemoryCampaignRepository, campaign_id: str
) -> campaign_repository.FindCampaignResponse:
    return repo.find(campaign_repository.FindCampaignRequest(campaign_id=campaign_id))


def test_row_golden_locks_the_storage_shape() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(views.save_request(campaign.Campaign(campaign_spec())))
    assert record_tuple(repo._rows["0123456789abcdef"]) == (
        "0123456789abcdef",
        "100.00",
        "USD",
        (("promo", "https://ok.example/x", campaign_repository.LinkStatus.ACTIVE),),
    )


def test_wire_golden_locks_the_campaign_payload() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(views.save_request(campaign.Campaign(campaign_spec())))
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
    repo.save(views.save_request(campaign.Campaign(campaign_spec())))
    handler = http.Handler(service.CampaignService(repo, FakeTargetPolicyAllowAll()))
    resp = handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))
    assert resp.status_code == 302
    assert resp.body == b""
    assert resp.headers == {"Location": "https://ok.example/x"}


def test_load_reconstructs_value_equal_non_identical() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    original = campaign.Campaign(campaign_spec())
    repo.save(views.save_request(original))
    loaded = views.required_campaign(_find(repo, "0123456789abcdef"), "0123456789abcdef")
    assert loaded is not original
    assert request_tuple(views.save_request(loaded)) == request_tuple(views.save_request(original))


def test_store_holds_rows_not_live_objects() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    original = campaign.Campaign(campaign_spec())
    repo.save(views.save_request(original))
    loaded = views.required_campaign(_find(repo, "0123456789abcdef"), "0123456789abcdef")
    loaded.add_short_link(short_link.ShortLinkSpec(slug="extra", target_url="https://ok.example/e", active=True))
    reloaded = views.required_campaign(_find(repo, "0123456789abcdef"), "0123456789abcdef")
    assert request_tuple(views.save_request(reloaded)) == request_tuple(views.save_request(original))


def test_load_reruns_invariants_on_stale_rows() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    repo.save(views.save_request(campaign.Campaign(campaign_spec())))
    row = repo._rows["0123456789abcdef"]
    stale = campaign_repository.CampaignRecord(
        id=row.id,
        budget=campaign_repository.MoneyRecord(amount="-5", currency=row.budget.currency),
        links=row.links,
    )
    repo._rows["0123456789abcdef"] = stale
    with pytest.raises(DomainError):
        views.required_campaign(_find(repo, "0123456789abcdef"), "0123456789abcdef")
