from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client


@ts.fake
class FakeCampaignRepository(ports.CampaignRepository):

    def __init__(self) -> None:
        self.rows: dict[str, ports.CampaignRecord] = {}
        self.saves: list[str] = []
        self.finds: list[str] = []

    def save(
        self, save_campaign_request: ports.SaveCampaignRequest
    ) -> ports.SaveCampaignResponse:
        self.saves.append(save_campaign_request.id)
        self.rows[save_campaign_request.id] = ports.CampaignRecord(
            id=save_campaign_request.id,
            window=save_campaign_request.window,
            links=save_campaign_request.links,
        )
        return ports.SaveCampaignResponse()

    def find(
        self, find_campaign_request: ports.FindCampaignRequest
    ) -> ports.FindCampaignResponse:
        self.finds.append(find_campaign_request.campaign_id)
        row = self.rows.get(find_campaign_request.campaign_id)
        if row is None:
            return ports.FindCampaignResponse(
                outcome=ports.CampaignLookup.MISSING, campaigns=()
            )
        return ports.FindCampaignResponse(
            outcome=ports.CampaignLookup.FOUND, campaigns=(row,)
        )


def test_creating_a_campaign_answers_the_view_of_what_was_built() -> None:
    campaign_service = application.CampaignService(FakeCampaignRepository())
    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    assert (campaign_view.campaign_id, campaign_view.links) == ("c1", ("spring-sale",))


def test_creating_a_campaign_with_no_links_answers_a_view_that_lists_nothing() -> None:
    campaign_service = application.CampaignService(FakeCampaignRepository())
    campaign_view = campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(),
        )
    )
    assert campaign_view.links == ()


def test_creating_a_campaign_stores_its_window_and_links() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    application.CampaignService(fake_campaign_repository).create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    stored = fake_campaign_repository.rows["c1"]
    assert (stored.window.start, stored.window.end) == ("2026-01-01", "2026-02-01")
    assert tuple((link.slug, link.target_url) for link in stored.links) == (
        ("spring-sale", "https://x.com"),
    )


def test_creating_a_campaign_with_a_bad_slug_is_refused_before_anything_is_stored() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="c1",
                window_start="2026-01-01",
                window_end="2026-02-01",
                links=(client.LinkBody(slug="BAD", target_url="https://x.com"),),
            )
        )
    assert ei.value.rejection.code == "bad_slug"
    assert ei.value.rejection.field == "links[0].slug"
    assert fake_campaign_repository.saves == []


def test_creating_a_campaign_with_a_backwards_window_is_refused() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="c1",
                window_start="2026-02-01",
                window_end="2026-01-01",
                links=(),
            )
        )
    assert ei.value.rejection.code == "window_order"
    assert fake_campaign_repository.saves == []


def test_creating_a_campaign_with_two_identical_slugs_is_refused() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).create_campaign(
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
    assert ei.value.rejection.code == "duplicate_slug"
    assert fake_campaign_repository.saves == []


def test_getting_a_campaign_that_was_never_created_is_not_found() -> None:
    campaign_service = application.CampaignService(FakeCampaignRepository())
    with pytest.raises(client.Missing) as ei:
        campaign_service.get_campaign(client.GetCampaignRequest(campaign_id="nope"))
    assert ei.value.code == "campaign_missing"
    assert ei.value.message == "no campaign 'nope'"


def test_getting_a_created_campaign_answers_its_links() -> None:
    campaign_service = application.CampaignService(FakeCampaignRepository())
    campaign_service.create_campaign(
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
    campaign_view = campaign_service.get_campaign(
        client.GetCampaignRequest(campaign_id="c1")
    )
    assert (campaign_view.campaign_id, campaign_view.links) == (
        "c1",
        ("alpha-one", "beta-two"),
    )


def test_adding_a_link_answers_a_view_of_every_link_and_stores_it() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    campaign_service = application.CampaignService(fake_campaign_repository)
    campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="alpha-one", target_url="https://a.com"),),
        )
    )
    campaign_view = campaign_service.add_link(
        client.AddLinkRequest(campaign_id="c1", slug="beta-two", target_url="https://b.com")
    )
    assert campaign_view.links == ("alpha-one", "beta-two")
    assert tuple(
        link.slug for link in fake_campaign_repository.rows["c1"].links
    ) == ("alpha-one", "beta-two")


def test_adding_a_link_with_two_bad_fields_reports_both_at_once() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).add_link(
            client.AddLinkRequest(campaign_id="c1", slug="BAD", target_url="ftp://nope")
        )
    assert ei.value.rejection.code == "validation_failed"
    assert {problem.code for problem in ei.value.rejection.problems} == {
        "bad_slug",
        "bad_target_url",
    }


def test_adding_a_link_validates_the_fields_before_the_repository_is_touched() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected):
        application.CampaignService(fake_campaign_repository).add_link(
            client.AddLinkRequest(campaign_id="c1", slug="BAD", target_url="ftp://nope")
        )
    assert fake_campaign_repository.finds == []
    assert fake_campaign_repository.saves == []


def test_adding_a_link_to_a_campaign_that_does_not_exist_is_not_found() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Missing) as ei:
        application.CampaignService(fake_campaign_repository).add_link(
            client.AddLinkRequest(
                campaign_id="nope", slug="spring-sale", target_url="https://x.com"
            )
        )
    assert ei.value.code == "campaign_missing"
    assert fake_campaign_repository.saves == []


def test_adding_a_link_whose_slug_is_already_taken_is_a_conflict() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    campaign_service = application.CampaignService(fake_campaign_repository)
    campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    with pytest.raises(client.Conflict) as ei:
        campaign_service.add_link(
            client.AddLinkRequest(
                campaign_id="c1", slug="spring-sale", target_url="https://y.com"
            )
        )
    assert ei.value.code == "duplicate_slug"
    assert fake_campaign_repository.saves == ["c1"]


def test_a_sixth_link_is_refused_at_the_cap() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    campaign_service = application.CampaignService(fake_campaign_repository)
    campaign_service.create_campaign(
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
    with pytest.raises(client.Conflict) as ei:
        campaign_service.add_link(
            client.AddLinkRequest(campaign_id="c1", slug="link-9", target_url="https://x.com")
        )
    assert ei.value.code == "too_many_links"


def test_deactivating_a_link_answers_the_campaign_and_stores_it() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    campaign_service = application.CampaignService(fake_campaign_repository)
    campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    campaign_view = campaign_service.deactivate_link(
        client.DeactivateLinkRequest(campaign_id="c1", slug="spring-sale")
    )
    assert campaign_view.campaign_id == "c1"
    assert campaign_view.links == ("spring-sale",)
    assert fake_campaign_repository.saves == ["c1", "c1"]


def test_deactivating_a_link_that_is_not_in_the_campaign_is_not_found() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    campaign_service = application.CampaignService(fake_campaign_repository)
    campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    with pytest.raises(client.Missing) as ei:
        campaign_service.deactivate_link(
            client.DeactivateLinkRequest(campaign_id="c1", slug="ghost-link")
        )
    assert ei.value.code == "link_missing"


def test_deactivating_a_link_on_a_campaign_that_does_not_exist_is_not_found() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Missing) as ei:
        application.CampaignService(fake_campaign_repository).deactivate_link(
            client.DeactivateLinkRequest(campaign_id="nope", slug="spring-sale")
        )
    assert ei.value.code == "campaign_missing"


def test_deactivating_a_link_named_by_an_invalid_slug_is_a_validation_failure() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    campaign_service = application.CampaignService(fake_campaign_repository)
    campaign_service.create_campaign(
        client.CreateCampaignRequest(
            campaign_id="c1",
            window_start="2026-01-01",
            window_end="2026-02-01",
            links=(client.LinkBody(slug="spring-sale", target_url="https://x.com"),),
        )
    )
    with pytest.raises(client.Rejected) as ei:
        campaign_service.deactivate_link(
            client.DeactivateLinkRequest(campaign_id="c1", slug="BAD")
        )
    assert ei.value.rejection.code == "bad_slug"


def test_an_empty_campaign_id_is_a_validation_failure_before_the_repository_is_read() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).get_campaign(
            client.GetCampaignRequest(campaign_id="")
        )
    assert ei.value.rejection.code == "bad_campaign_id"
    assert fake_campaign_repository.finds == []


def test_deactivating_with_an_empty_campaign_id_is_a_validation_failure() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).deactivate_link(
            client.DeactivateLinkRequest(campaign_id="", slug="spring-sale")
        )
    assert ei.value.rejection.code == "bad_campaign_id"
    assert fake_campaign_repository.finds == []


def test_adding_a_link_collects_the_campaign_id_problem_with_its_siblings() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).add_link(
            client.AddLinkRequest(campaign_id="", slug="BAD", target_url="ftp://x")
        )
    assert ei.value.rejection.code == "validation_failed"
    assert [p.field for p in ei.value.rejection.problems] == [
        "campaign_id",
        "slug",
        "target_url",
    ]
    assert fake_campaign_repository.finds == []


def test_creating_a_campaign_with_an_empty_id_is_refused_before_anything_is_stored() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    with pytest.raises(client.Rejected) as ei:
        application.CampaignService(fake_campaign_repository).create_campaign(
            client.CreateCampaignRequest(
                campaign_id="",
                window_start="2026-01-01",
                window_end="2026-02-01",
                links=(),
            )
        )
    assert ei.value.rejection.code == "bad_campaign_id"
    assert fake_campaign_repository.saves == []


def test_a_stored_record_with_a_corrupt_slug_is_unreadable_not_a_rejection() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    fake_campaign_repository.rows["c1"] = ports.CampaignRecord(
        id="c1",
        window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(ports.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),),
    )
    with pytest.raises(client.Unreadable) as ei:
        application.CampaignService(fake_campaign_repository).get_campaign(
            client.GetCampaignRequest(campaign_id="c1")
        )
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_corrupt_stored_record_keeps_the_domain_complaint_as_its_cause() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    fake_campaign_repository.rows["c1"] = ports.CampaignRecord(
        id="c1",
        window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
        links=(ports.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),),
    )
    with pytest.raises(client.Unreadable) as ei:
        application.CampaignService(fake_campaign_repository).get_campaign(
            client.GetCampaignRequest(campaign_id="c1")
        )
    cause = ei.value.__cause__
    assert isinstance(cause, Exception)
    assert "bad_slug" in str(cause)


def test_a_stored_record_with_a_backwards_window_is_unreadable() -> None:
    fake_campaign_repository = FakeCampaignRepository()
    fake_campaign_repository.rows["c1"] = ports.CampaignRecord(
        id="c1",
        window=ports.WindowRecord(start="2026-02-01", end="2026-01-01"),
        links=(),
    )
    with pytest.raises(client.Unreadable) as ei:
        application.CampaignService(fake_campaign_repository).get_campaign(
            client.GetCampaignRequest(campaign_id="c1")
        )
    assert str(ei.value).startswith("corrupted campaign record 'c1': ")


def test_a_found_record_becomes_the_parts_a_campaign_is_rebuilt_from() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.FOUND,
        campaigns=(
            ports.CampaignRecord(
                id="c1",
                window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(
                    ports.LinkRecord(slug="spring-sale", target_url="https://x.com"),
                ),
            ),
        ),
    )
    campaign_spec = application.MapToCampaignSpec(
        find_campaign_request=ports.FindCampaignRequest(campaign_id="c1"),
        find_campaign_response=find_campaign_response,
    )
    assert campaign_spec.id == "c1"
    assert (
        campaign_spec.window.start,
        campaign_spec.window.end,
    ) == ("2026-01-01", "2026-02-01")
    assert tuple(
        (link.slug, link.target_url) for link in campaign_spec.links
    ) == (("spring-sale", "https://x.com"),)


def test_a_missing_outcome_is_a_not_found_naming_the_campaign() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.MISSING, campaigns=()
    )
    with pytest.raises(client.Missing) as ei:
        application.MapToCampaignSpec(
            find_campaign_request=ports.FindCampaignRequest(campaign_id="c9"),
            find_campaign_response=find_campaign_response,
        )
    assert ei.value.code == "campaign_missing"
    assert ei.value.message == "no campaign 'c9'"


def test_a_record_with_a_corrupt_slug_still_exposes_the_slug_the_repository_gave() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.FOUND,
        campaigns=(
            ports.CampaignRecord(
                id="c1",
                window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(ports.LinkRecord(slug="BAD SLUG", target_url="https://x.com"),),
            ),
        ),
    )
    campaign_spec = application.MapToCampaignSpec(
        find_campaign_request=ports.FindCampaignRequest(campaign_id="c1"),
        find_campaign_response=find_campaign_response,
    )
    assert campaign_spec.links[0].slug == "BAD SLUG"


def test_a_sound_record_exposes_every_link_it_carried_in_order() -> None:
    find_campaign_response = ports.FindCampaignResponse(
        outcome=ports.CampaignLookup.FOUND,
        campaigns=(
            ports.CampaignRecord(
                id="c1",
                window=ports.WindowRecord(start="2026-01-01", end="2026-02-01"),
                links=(
                    ports.LinkRecord(slug="alpha-one", target_url="https://a.com"),
                    ports.LinkRecord(slug="beta-two", target_url="https://b.com"),
                ),
            ),
        ),
    )
    campaign_spec = application.MapToCampaignSpec(
        find_campaign_request=ports.FindCampaignRequest(campaign_id="c1"),
        find_campaign_response=find_campaign_response,
    )
    assert tuple(link.slug for link in campaign_spec.links) == (
        "alpha-one",
        "beta-two",
    )
