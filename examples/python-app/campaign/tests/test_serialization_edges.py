from __future__ import annotations

import typing

import pytest
import tesser.testing as ts

import campaign.adapters.gateways.campaign_identity as campaign_identity
import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.adapters.handlers.http as http
import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.domain.campaign as campaign
import campaign.domain.money as money
import campaign.domain.short_link as short_link
import campaign.domain.short_links as short_links
from tesser.errors import DomainError, not_found
from protocol.http import HttpRequest


def _shape(  # tesser:debt TB071
    id_: str, budget: campaign_repository.MoneyRecord, links: tuple[campaign_repository.LinkRecord, ...]
) -> tuple[object, ...]:
    return (
        id_,
        budget.amount,
        budget.currency,
        tuple((link.slug, link.target_url, link.status) for link in links),
    )


def record_tuple(record: campaign_repository.CampaignRecord) -> tuple[object, ...]:  # tesser:debt TB071
    return _shape(record.id, record.budget, record.links)


def request_tuple(request: campaign_repository.SaveCampaignRequest) -> tuple[object, ...]:  # tesser:debt TB071
    return _shape(request.id, request.budget, request.links)


@ts.helper
def campaign_spec(slug: str = "promo") -> campaign.CampaignSpec:
    return campaign.CampaignSpec(
        id="0123456789abcdef",
        budget=money.MoneySpec(amount="100.00", currency="USD"),
        links=short_links.ShortLinksSpec(links=(short_link.ShortLinkSpec(slug=slug, target_url="https://ok.example/x", active=True),)),
    )


@ts.fake
class FakeTargetPolicyAllowAll(target_policy.TargetPolicy):
    def check(self, request: target_policy.CheckTargetRequest) -> target_policy.CheckTargetResponse:
        return target_policy.CheckTargetResponse(verdict=target_policy.PolicyVerdict.ALLOWED, reason="ok")


def _find(  # tesser:debt TB071
    repo: repo_memory.InMemoryCampaignRepository, campaign_id: str
) -> campaign_repository.FindCampaignResponse:
    return repo.find(campaign_repository.FindCampaignRequest(campaign_id=campaign_id))


def test_row_golden_locks_the_storage_shape() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    saved = campaign.Campaign(campaign_spec())
    repo.save(campaign_repository.SaveCampaignRequest(
        id=str(saved.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(saved.budget.amount), currency=str(saved.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in saved.links
        ),
    ))
    assert record_tuple(repo._rows["0123456789abcdef"]) == (
        "0123456789abcdef",
        "100.00",
        "USD",
        (("promo", "https://ok.example/x", "active"),),
    )


def test_wire_golden_locks_the_campaign_payload() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    saved = campaign.Campaign(campaign_spec())
    repo.save(campaign_repository.SaveCampaignRequest(
        id=str(saved.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(saved.budget.amount), currency=str(saved.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in saved.links
        ),
    ))
    handler = http.Handler(service.CampaignService(repo, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), repo))
    resp = handler.get_campaign(HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b""))
    assert resp.status_code == 200
    assert resp.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "status": "active"}],
    }


def test_wire_golden_locks_resolve_as_a_real_redirect() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    saved = campaign.Campaign(campaign_spec())
    repo.save(campaign_repository.SaveCampaignRequest(
        id=str(saved.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(saved.budget.amount), currency=str(saved.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in saved.links
        ),
    ))
    handler = http.Handler(service.CampaignService(repo, FakeTargetPolicyAllowAll(), campaign_identity.SecretsCampaignIdentity(), repo))
    resp = handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))
    assert resp.status_code == 302
    assert resp.body == b""
    assert resp.headers == {"Location": "https://ok.example/x"}


def test_load_reconstructs_value_equal_non_identical() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    original = campaign.Campaign(campaign_spec())
    repo.save(campaign_repository.SaveCampaignRequest(
        id=str(original.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    ))
    found = _find(repo, "0123456789abcdef")
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            record = found.campaigns[0]
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
        case _ as unreachable:
            typing.assert_never(unreachable)
    loaded = campaign.Campaign(campaign.CampaignSpec(
        id=record.id,
        budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=short_links.ShortLinksSpec(links=tuple(
            short_link.ShortLinkSpec(
                slug=link.slug, target_url=link.target_url, active=link.status == "active"
            )
            for link in record.links
        )),
    ))
    assert loaded is not original
    assert request_tuple(campaign_repository.SaveCampaignRequest(
        id=str(loaded.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(loaded.budget.amount), currency=str(loaded.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in loaded.links
        ),
    )) == request_tuple(campaign_repository.SaveCampaignRequest(
        id=str(original.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    ))


def test_store_holds_rows_not_live_objects() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    original = campaign.Campaign(campaign_spec())
    repo.save(campaign_repository.SaveCampaignRequest(
        id=str(original.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    ))
    found = _find(repo, "0123456789abcdef")
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            record = found.campaigns[0]
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
        case _ as unreachable:
            typing.assert_never(unreachable)
    loaded = campaign.Campaign(campaign.CampaignSpec(
        id=record.id,
        budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=short_links.ShortLinksSpec(links=tuple(
            short_link.ShortLinkSpec(
                slug=link.slug, target_url=link.target_url, active=link.status == "active"
            )
            for link in record.links
        )),
    ))
    loaded.add_short_link(short_link.ShortLinkSpec(slug="extra", target_url="https://ok.example/e", active=True))
    found = _find(repo, "0123456789abcdef")
    match found.outcome:
        case campaign_repository.CampaignLookup.FOUND:
            record = found.campaigns[0]
        case campaign_repository.CampaignLookup.MISSING:
            raise not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
        case _ as unreachable:
            typing.assert_never(unreachable)
    reloaded = campaign.Campaign(campaign.CampaignSpec(
        id=record.id,
        budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=short_links.ShortLinksSpec(links=tuple(
            short_link.ShortLinkSpec(
                slug=link.slug, target_url=link.target_url, active=link.status == "active"
            )
            for link in record.links
        )),
    ))
    assert request_tuple(campaign_repository.SaveCampaignRequest(
        id=str(reloaded.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(reloaded.budget.amount), currency=str(reloaded.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in reloaded.links
        ),
    )) == request_tuple(campaign_repository.SaveCampaignRequest(
        id=str(original.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    ))


def test_load_reruns_invariants_on_stale_rows() -> None:
    repo = repo_memory.InMemoryCampaignRepository()
    saved = campaign.Campaign(campaign_spec())
    repo.save(campaign_repository.SaveCampaignRequest(
        id=str(saved.id),
        budget=campaign_repository.MoneyRecord(
            amount=str(saved.budget.amount), currency=str(saved.budget.currency)
        ),
        links=tuple(
            campaign_repository.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in saved.links
        ),
    ))
    row = repo._rows["0123456789abcdef"]
    stale = campaign_repository.CampaignRecord(
        id=row.id,
        budget=campaign_repository.MoneyRecord(amount="-5", currency=row.budget.currency),
        links=row.links,
    )
    repo._rows["0123456789abcdef"] = stale
    with pytest.raises(DomainError):
        found = _find(repo, "0123456789abcdef")
        match found.outcome:
            case campaign_repository.CampaignLookup.FOUND:
                record = found.campaigns[0]
            case campaign_repository.CampaignLookup.MISSING:
                raise not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
            case _ as unreachable:
                typing.assert_never(unreachable)
        reloaded = campaign.Campaign(campaign.CampaignSpec(
            id=record.id,
            budget=money.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
            links=short_links.ShortLinksSpec(links=tuple(
                short_link.ShortLinkSpec(
                    slug=link.slug, target_url=link.target_url, active=link.status == "active"
                )
                for link in record.links
            )),
        ))
