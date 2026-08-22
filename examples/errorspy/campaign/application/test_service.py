from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application.ports.campaign_repository as campaign_repository
import campaign.application.service as service
import campaign.client.client as client
from tesser.errors import DomainError, InfraError, Kind


@ts.fake
class FakeCampaignRepository(campaign_repository.CampaignRepository):

    def __init__(self) -> None:
        self.rows: dict[str, campaign_repository.CampaignRecord] = {}
        self.saves: list[str] = []
        self.finds: list[str] = []

    def save(
        self, request: campaign_repository.SaveCampaignRequest
    ) -> campaign_repository.SaveCampaignResponse:
        self.saves.append(request.id)
        self.rows[request.id] = campaign_repository.CampaignRecord(
            id=request.id, window=request.window, links=request.links
        )
        return campaign_repository.SaveCampaignResponse()

    def find(
        self, request: campaign_repository.FindCampaignRequest
    ) -> campaign_repository.FindCampaignResponse:
        self.finds.append(request.campaign_id)
        row = self.rows.get(request.campaign_id)
        if row is None:
            return campaign_repository.FindCampaignResponse(
                outcome=campaign_repository.CampaignLookup.MISSING, campaigns=()
            )
        return campaign_repository.FindCampaignResponse(
            outcome=campaign_repository.CampaignLookup.FOUND, campaigns=(row,)
        )


def test_creating_a_campaign_answers_the_view_of_what_was_built() -> None:
    svc = service.CampaignService(FakeCampaignRepository())
    view = svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    assert (view.campaign_id, view.links) == ("c1", ("spring-sale",))


def test_creating_a_campaign_with_no_links_answers_a_view_that_lists_nothing() -> None:
    svc = service.CampaignService(FakeCampaignRepository())
    view = svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(),
        )
    )
    assert view.links == ()


def test_creating_a_campaign_stores_its_window_and_links() -> None:
    repo = FakeCampaignRepository()
    service.CampaignService(repo).create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    stored = repo.rows["c1"]
    assert (stored.window.start, stored.window.end) == ("2026-01-01", "2026-02-01")
    assert tuple((link.slug, link.target_url) for link in stored.links) == (
        ("spring-sale", "https://x.com"),
    )


def test_creating_a_campaign_with_a_bad_slug_is_refused_before_anything_is_stored() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="c1",
                window_start="2026-01-01",
                window_end="2026-02-01",
                links=(client.LinkBody(slug="BAD", target_url="https://x.com"),),
            )
        )
    assert ei.value.kind is Kind.VALIDATION
    assert ei.value.code == "bad_slug"
    assert ei.value.field == "links[0].slug"
    assert repo.saves == []


def test_creating_a_campaign_with_a_backwards_window_is_refused() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="c1",
                window_start="2026-02-01",
                window_end="2026-01-01",
                links=(),
            )
        )
    assert ei.value.code == "window_order"
    assert repo.saves == []


def test_creating_a_campaign_with_two_identical_slugs_is_a_conflict() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="c1",
                window_start="2026-01-01",
                window_end="2026-02-01",
                links=(
                    client.LinkBody(slug="spring-sale", target_url="https://x.com"),
                    client.LinkBody(slug="spring-sale", target_url="https://y.com"),
                ),
            )
        )
    assert ei.value.kind is Kind.CONFLICT
    assert ei.value.code == "duplicate_slug"
    assert repo.saves == []


def test_getting_a_campaign_that_was_never_created_is_not_found() -> None:
    svc = service.CampaignService(FakeCampaignRepository())
    with pytest.raises(DomainError) as ei:
        svc.get_campaign(client.GetCampaignRequest(campaign_id="nope"))
    assert ei.value.kind is Kind.NOT_FOUND
    assert ei.value.code == "campaign_missing"
    assert ei.value.message == "no campaign 'nope'"


def test_getting_a_created_campaign_answers_its_links() -> None:
    svc = service.CampaignService(FakeCampaignRepository())
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(
                client.LinkBody(slug="alpha-one", target_url="https://a.com"),
                client.LinkBody(slug="beta-two", target_url="https://b.com"),
            ),
        )
    )
    view = svc.get_campaign(client.GetCampaignRequest(campaign_id="c1"))
    assert (view.campaign_id, view.links) == ("c1", ("alpha-one", "beta-two"))


def test_adding_a_link_answers_a_view_of_every_link_and_stores_it() -> None:
    repo = FakeCampaignRepository()
    svc = service.CampaignService(repo)
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="alpha-one", target_url="https://a.com"),),
        )
    )
    view = svc.add_link(
        client.AddLinkRequest(campaign_id="c1", slug="beta-two", target_url="https://b.com")
    )
    assert view.links == ("alpha-one", "beta-two")
    assert tuple(link.slug for link in repo.rows["c1"].links) == ("alpha-one", "beta-two")


def test_adding_a_link_with_two_bad_fields_reports_both_at_once() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).add_link(
            client.AddLinkRequest(campaign_id="c1", slug="BAD", target_url="ftp://nope")
        )
    assert ei.value.code == "validation_failed"
    assert {problem.code for problem in ei.value.problems} == {"bad_slug", "bad_target_url"}


def test_adding_a_link_validates_the_fields_before_the_repository_is_touched() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError):
        service.CampaignService(repo).add_link(
            client.AddLinkRequest(campaign_id="c1", slug="BAD", target_url="ftp://nope")
        )
    assert repo.finds == []
    assert repo.saves == []


def test_adding_a_link_to_a_campaign_that_does_not_exist_is_not_found() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).add_link(
            client.AddLinkRequest(
                campaign_id="nope", slug="spring-sale", target_url="https://x.com"
            )
        )
    assert ei.value.code == "campaign_missing"
    assert repo.saves == []


def test_adding_a_link_whose_slug_is_already_taken_is_a_conflict() -> None:
    repo = FakeCampaignRepository()
    svc = service.CampaignService(repo)
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    with pytest.raises(DomainError) as ei:
        svc.add_link(
            client.AddLinkRequest(
                campaign_id="c1", slug="spring-sale", target_url="https://y.com"
            )
        )
    assert ei.value.kind is Kind.CONFLICT
    assert ei.value.code == "duplicate_slug"
    assert repo.saves == ["c1"]


def test_a_sixth_link_is_refused_at_the_cap() -> None:
    repo = FakeCampaignRepository()
    svc = service.CampaignService(repo)
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=tuple(
                client.LinkBody(slug=f"link-{n}", target_url="https://x.com")
                for n in range(5)
            ),
        )
    )
    with pytest.raises(DomainError) as ei:
        svc.add_link(
            client.AddLinkRequest(campaign_id="c1", slug="link-9", target_url="https://x.com")
        )
    assert ei.value.kind is Kind.CONFLICT
    assert ei.value.code == "too_many_links"


def test_deactivating_a_link_answers_the_campaign_and_stores_it() -> None:
    repo = FakeCampaignRepository()
    svc = service.CampaignService(repo)
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    view = svc.deactivate_link(
        client.DeactivateLinkRequest(campaign_id="c1", slug="spring-sale")
    )
    assert view.campaign_id == "c1"
    assert view.links == ("spring-sale",)
    assert repo.saves == ["c1", "c1"]


def test_deactivating_a_link_that_is_not_in_the_campaign_is_not_found() -> None:
    repo = FakeCampaignRepository()
    svc = service.CampaignService(repo)
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    with pytest.raises(DomainError) as ei:
        svc.deactivate_link(
            client.DeactivateLinkRequest(campaign_id="c1", slug="ghost-link")
        )
    assert ei.value.kind is Kind.NOT_FOUND
    assert ei.value.code == "link_missing"


def test_deactivating_a_link_on_a_campaign_that_does_not_exist_is_not_found() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).deactivate_link(
            client.DeactivateLinkRequest(campaign_id="nope", slug="spring-sale")
        )
    assert ei.value.code == "campaign_missing"


def test_deactivating_a_link_named_by_an_invalid_slug_is_a_validation_failure() -> None:
    repo = FakeCampaignRepository()
    svc = service.CampaignService(repo)
    svc.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    with pytest.raises(DomainError) as ei:
        svc.deactivate_link(client.DeactivateLinkRequest(campaign_id="c1", slug="BAD"))
    assert ei.value.kind is Kind.VALIDATION
    assert ei.value.code == "bad_slug"


def test_an_empty_campaign_id_is_a_validation_failure_before_the_repository_is_read() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).get_campaign(client.GetCampaignRequest(campaign_id=""))
    assert ei.value.kind is Kind.VALIDATION
    assert ei.value.code == "bad_campaign_id"
    assert repo.finds == []


def test_deactivating_with_an_empty_campaign_id_is_a_validation_failure() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).deactivate_link(
            client.DeactivateLinkRequest(campaign_id="", slug="spring-sale")
        )
    assert ei.value.kind is Kind.VALIDATION
    assert ei.value.code == "bad_campaign_id"
    assert repo.finds == []


def test_adding_a_link_collects_the_campaign_id_problem_with_its_siblings() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).add_link(
            client.AddLinkRequest(campaign_id="", slug="BAD", target_url="ftp://x")
        )
    assert ei.value.kind is Kind.VALIDATION
    assert ei.value.code == "validation_failed"
    assert [p.field for p in ei.value.problems] == ["campaign_id", "slug", "target_url"]
    assert repo.finds == []


def test_creating_a_campaign_with_an_empty_id_is_refused_before_anything_is_stored() -> None:
    repo = FakeCampaignRepository()
    with pytest.raises(DomainError) as ei:
        service.CampaignService(repo).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="",
                window_start="2026-01-01",
                window_end="2026-02-01",
                links=(),
            )
        )
    assert ei.value.kind is Kind.VALIDATION
    assert ei.value.code == "bad_campaign_id"
    assert repo.saves == []


def test_a_stored_record_with_a_corrupt_slug_is_infrastructure_not_validation() -> None:
    repo = FakeCampaignRepository()
    repo.rows["c1"] = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(
            campaign_repository.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),
        ),
    )
    with pytest.raises(InfraError) as ei:
        service.CampaignService(repo).get_campaign(
            client.GetCampaignRequest(campaign_id="c1")
        )
    assert not isinstance(ei.value, DomainError)
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_corrupt_stored_record_keeps_the_domain_complaint_as_its_cause() -> None:
    repo = FakeCampaignRepository()
    repo.rows["c1"] = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(
            campaign_repository.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),
        ),
    )
    with pytest.raises(InfraError) as ei:
        service.CampaignService(repo).get_campaign(
            client.GetCampaignRequest(campaign_id="c1")
        )
    cause = ei.value.__cause__
    assert isinstance(cause, DomainError)
    assert cause.kind is Kind.VALIDATION
    assert cause.code == "bad_slug"


def test_a_stored_record_with_a_backwards_window_is_an_infrastructure_failure() -> None:
    repo = FakeCampaignRepository()
    repo.rows["c1"] = campaign_repository.CampaignRecord(
        id="c1",
        window=campaign_repository.WindowRecord(start="2026-02-01", end="2026-01-01"),
        links=(),
    )
    with pytest.raises(InfraError) as ei:
        service.CampaignService(repo).get_campaign(
            client.GetCampaignRequest(campaign_id="c1")
        )
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")
