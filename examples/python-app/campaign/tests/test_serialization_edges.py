from __future__ import annotations

import typing

import pytest
import tesser.testing as ts

import campaign.adapters.gateways as gateways
import campaign.adapters.handlers as handlers
import campaign.adapters.repositories as repositories
import campaign.application as application
import campaign.application.ports as ports
import campaign.domain as domain
import protocol as protocol
import tesser.errors as errors


@ts.helper
def campaign_spec(slug: str = "promo") -> domain.CampaignSpec:
    return domain.CampaignSpec(
        id="0123456789abcdef",
        budget=domain.MoneySpec(amount="100.00", currency="USD"),
        links=domain.ShortLinksSpec(links=(domain.ShortLinkSpec(slug=slug, target_url="https://ok.example/x", active=True),)),
    )


@ts.fake
class FakeTargetPolicyAllowAll(ports.TargetPolicy):
    def check(self, check_target_request: ports.CheckTargetRequest) -> ports.CheckTargetResponse:
        return ports.CheckTargetResponse(verdict=ports.PolicyVerdict.ALLOWED, reason="ok")


def test_row_golden_locks_the_storage_shape() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign = domain.Campaign(campaign_spec())
    in_memory_campaign_repository.save(ports.SaveCampaignRequest(
        id=str(campaign.id),
        budget=ports.MoneyRecord(
            amount=str(campaign.budget.amount), currency=str(campaign.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in campaign.links
        ),
    ))
    assert in_memory_campaign_repository._rows["0123456789abcdef"] == ports.CampaignRecord(
        id="0123456789abcdef",
        budget=ports.MoneyRecord(amount="100.00", currency="USD"),
        links=(
            ports.LinkRecord(
                slug="promo", target_url="https://ok.example/x", status="active"
            ),
        ),
    )


def test_wire_golden_locks_the_campaign_payload() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign = domain.Campaign(campaign_spec())
    in_memory_campaign_repository.save(ports.SaveCampaignRequest(
        id=str(campaign.id),
        budget=ports.MoneyRecord(
            amount=str(campaign.budget.amount), currency=str(campaign.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in campaign.links
        ),
    ))
    http_handler = handlers.HttpHandler(application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository))
    http_response = http_handler.get_campaign(protocol.HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b""))
    assert http_response.status_code == 200
    assert http_response.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [{"slug": "promo", "target_url": "https://ok.example/x", "status": "active"}],
    }


def test_wire_golden_locks_resolve_as_a_real_redirect() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign = domain.Campaign(campaign_spec())
    in_memory_campaign_repository.save(ports.SaveCampaignRequest(
        id=str(campaign.id),
        budget=ports.MoneyRecord(
            amount=str(campaign.budget.amount), currency=str(campaign.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in campaign.links
        ),
    ))
    http_handler = handlers.HttpHandler(application.CampaignService(in_memory_campaign_repository, FakeTargetPolicyAllowAll(), gateways.SecretsCampaignIdentity(), in_memory_campaign_repository))
    http_response = http_handler.resolve(protocol.HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))
    assert http_response.status_code == 302
    assert http_response.body == b""
    assert http_response.headers == {"Location": "https://ok.example/x"}


def test_load_reconstructs_value_equal_non_identical() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    original = domain.Campaign(campaign_spec())
    in_memory_campaign_repository.save(ports.SaveCampaignRequest(
        id=str(original.id),
        budget=ports.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    ))
    find_campaign_response = in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))
    match find_campaign_response.outcome:
        case ports.CampaignLookup.FOUND:
            record = find_campaign_response.campaigns[0]
        case ports.CampaignLookup.MISSING:
            raise errors.not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
        case _ as unreachable:
            typing.assert_never(unreachable)
    loaded = domain.Campaign(domain.CampaignSpec(
        id=record.id,
        budget=domain.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=domain.ShortLinksSpec(links=tuple(
            domain.ShortLinkSpec(
                slug=link.slug, target_url=link.target_url, active=link.status == "active"
            )
            for link in record.links
        )),
    ))
    assert loaded is not original
    assert ports.SaveCampaignRequest(
        id=str(loaded.id),
        budget=ports.MoneyRecord(
            amount=str(loaded.budget.amount), currency=str(loaded.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in loaded.links
        ),
    ) == ports.SaveCampaignRequest(
        id=str(original.id),
        budget=ports.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    )


def test_store_holds_rows_not_live_objects() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    original = domain.Campaign(campaign_spec())
    in_memory_campaign_repository.save(ports.SaveCampaignRequest(
        id=str(original.id),
        budget=ports.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    ))
    find_campaign_response = in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))
    match find_campaign_response.outcome:
        case ports.CampaignLookup.FOUND:
            record = find_campaign_response.campaigns[0]
        case ports.CampaignLookup.MISSING:
            raise errors.not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
        case _ as unreachable:
            typing.assert_never(unreachable)
    loaded = domain.Campaign(domain.CampaignSpec(
        id=record.id,
        budget=domain.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=domain.ShortLinksSpec(links=tuple(
            domain.ShortLinkSpec(
                slug=link.slug, target_url=link.target_url, active=link.status == "active"
            )
            for link in record.links
        )),
    ))
    loaded.add_short_link(domain.ShortLinkSpec(slug="extra", target_url="https://ok.example/e", active=True))
    find_campaign_response = in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))
    match find_campaign_response.outcome:
        case ports.CampaignLookup.FOUND:
            record = find_campaign_response.campaigns[0]
        case ports.CampaignLookup.MISSING:
            raise errors.not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
        case _ as unreachable:
            typing.assert_never(unreachable)
    reloaded = domain.Campaign(domain.CampaignSpec(
        id=record.id,
        budget=domain.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
        links=domain.ShortLinksSpec(links=tuple(
            domain.ShortLinkSpec(
                slug=link.slug, target_url=link.target_url, active=link.status == "active"
            )
            for link in record.links
        )),
    ))
    assert ports.SaveCampaignRequest(
        id=str(reloaded.id),
        budget=ports.MoneyRecord(
            amount=str(reloaded.budget.amount), currency=str(reloaded.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in reloaded.links
        ),
    ) == ports.SaveCampaignRequest(
        id=str(original.id),
        budget=ports.MoneyRecord(
            amount=str(original.budget.amount), currency=str(original.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in original.links
        ),
    )


def test_load_reruns_invariants_on_stale_rows() -> None:
    in_memory_campaign_repository = repositories.InMemoryCampaignRepository()
    campaign = domain.Campaign(campaign_spec())
    in_memory_campaign_repository.save(ports.SaveCampaignRequest(
        id=str(campaign.id),
        budget=ports.MoneyRecord(
            amount=str(campaign.budget.amount), currency=str(campaign.budget.currency)
        ),
        links=tuple(
            ports.LinkRecord(
                slug=str(link.slug), target_url=str(link.target_url), status=str(link.status)
            )
            for link in campaign.links
        ),
    ))
    row = in_memory_campaign_repository._rows["0123456789abcdef"]
    campaign_record = ports.CampaignRecord(
        id=row.id,
        budget=ports.MoneyRecord(amount="-5", currency=row.budget.currency),
        links=row.links,
    )
    in_memory_campaign_repository._rows["0123456789abcdef"] = campaign_record
    with pytest.raises(errors.DomainError):
        find_campaign_response = in_memory_campaign_repository.find(ports.FindCampaignRequest(campaign_id="0123456789abcdef"))
        match find_campaign_response.outcome:
            case ports.CampaignLookup.FOUND:
                record = find_campaign_response.campaigns[0]
            case ports.CampaignLookup.MISSING:
                raise errors.not_found("campaign_missing", "no campaign with id '0123456789abcdef'")
            case _ as unreachable:
                typing.assert_never(unreachable)
        reloaded = domain.Campaign(domain.CampaignSpec(
            id=record.id,
            budget=domain.MoneySpec(amount=record.budget.amount, currency=record.budget.currency),
            links=domain.ShortLinksSpec(links=tuple(
                domain.ShortLinkSpec(
                    slug=link.slug, target_url=link.target_url, active=link.status == "active"
                )
                for link in record.links
            )),
        ))
