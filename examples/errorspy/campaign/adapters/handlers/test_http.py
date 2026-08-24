from __future__ import annotations

import json

import tesser.testing as ts

import campaign.adapters.handlers.http as handlers
import campaign.client.client as client
import tesser.errors as errors


@ts.fake
class FakeCampaignClient(client.Client):

    def __init__(
        self,
        view: client.CampaignView | None = None,
        error: Exception | None = None,
    ) -> None:
        self.view = view
        self.error = error
        self.requests: list[object] = []

    def create_campaign(self, req: client.CreateCampaignRequest) -> client.CampaignView:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view

    def get_campaign(self, req: client.GetCampaignRequest) -> client.CampaignView:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view

    def add_link(self, req: client.AddLinkRequest) -> client.CampaignView:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view

    def deactivate_link(self, req: client.DeactivateLinkRequest) -> client.CampaignView:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view


def test_creating_a_campaign_answers_201_with_the_id() -> None:
    resp = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    assert resp.status == 201
    assert resp.body == {"id": "c1"}


def test_creating_a_campaign_hands_the_client_the_parsed_body() -> None:
    fake = FakeCampaignClient()
    handlers.Handler(fake).create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    req = fake.requests[0]
    assert isinstance(req, client.CreateCampaignRequest)
    assert (req.campaign_id, req.window_start, req.window_end) == (
        "c1",
        "2026-01-01",
        "2026-02-01",
    )
    assert tuple((link.slug, link.target_url) for link in req.links) == (
        ("spring-sale", "https://x.com"),
    )


def test_a_body_that_is_not_json_is_400_and_the_client_is_never_called() -> None:
    fake = FakeCampaignClient()
    resp = handlers.Handler(fake).create_campaign("c1", "{not json")
    assert resp.status == 400
    assert resp.body["type"] == "/problems/malformed_request"
    assert resp.body["title"] == "Bad Request"
    assert resp.body["status"] == 400
    assert str(resp.body["detail"]).startswith("malformed JSON: ")
    assert fake.requests == []


def test_a_json_array_body_is_400_because_the_top_level_must_be_an_object() -> None:
    fake = FakeCampaignClient()
    resp = handlers.Handler(fake).create_campaign("c1", "[1, 2]")
    assert resp.status == 400
    assert resp.body["detail"] == "expected a JSON object"
    assert fake.requests == []


def test_a_json_scalar_body_is_400_because_the_top_level_must_be_an_object() -> None:
    fake = FakeCampaignClient()
    resp = handlers.Handler(fake).create_campaign("c1", "7")
    assert resp.status == 400
    assert resp.body["detail"] == "expected a JSON object"
    assert fake.requests == []


def test_a_window_that_is_not_an_object_is_400_naming_the_field() -> None:
    resp = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1", json.dumps({"window": "2026-01-01", "links": []})
    )
    assert resp.status == 400
    assert resp.body["detail"] == "'window' must be an object"


def test_links_that_are_not_an_array_is_400_naming_the_field() -> None:
    resp = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps({"window": {"start": "2026-01-01", "end": "2026-02-01"}, "links": {}}),
    )
    assert resp.status == 400
    assert resp.body["detail"] == "'links' must be an array"


def test_a_link_entry_that_is_not_an_object_is_400() -> None:
    resp = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps(
            {"window": {"start": "2026-01-01", "end": "2026-02-01"}, "links": ["nope"]}
        ),
    )
    assert resp.status == 400
    assert resp.body["detail"] == "'link' must be an object"


def test_a_window_start_that_is_not_a_string_is_400() -> None:
    resp = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps({"window": {"start": 20260101, "end": "2026-02-01"}, "links": []}),
    )
    assert resp.status == 400
    assert resp.body["detail"] == "expected a string field"


def test_a_validation_failure_is_422_carrying_the_code_title_and_field() -> None:
    fake = FakeCampaignClient(
        error=errors.invalid("bad_slug", "invalid slug 'BAD'", field="links[0].slug")
    )
    resp = handlers.Handler(fake).create_campaign(
        "c1", json.dumps({"window": {"start": "2026-01-01", "end": "2026-02-01"}, "links": []})
    )
    assert resp.body == {
        "type": "/problems/bad_slug",
        "title": "bad slug",
        "status": 422,
        "detail": "invalid slug 'BAD'",
        "field": "links[0].slug",
    }
    assert resp.status == 422


def test_an_aggregated_validation_failure_lists_every_invalid_param() -> None:
    fake = FakeCampaignClient(
        error=errors.DomainError(
            errors.Kind.VALIDATION,
            "validation_failed",
            "one or more fields are invalid",
            problems=(
                errors.NeedsDesignFieldProblem("bad_slug", "slug", "invalid slug 'BAD'"),
                errors.NeedsDesignFieldProblem("bad_target_url", "target_url", "invalid target url 'ftp://x'"),
            ),
        )
    )
    resp = handlers.Handler(fake).add_link(
        "c1", json.dumps({"slug": "BAD", "target_url": "ftp://x"})
    )
    assert resp.status == 422
    assert resp.body["invalid-params"] == [
        {"name": "slug", "code": "bad_slug", "reason": "invalid slug 'BAD'"},
        {"name": "target_url", "code": "bad_target_url", "reason": "invalid target url 'ftp://x'"},
    ]
    assert "field" not in resp.body


def test_a_missing_campaign_is_404() -> None:
    fake = FakeCampaignClient(error=errors.not_found("campaign_missing", "no campaign 'nope'"))
    resp = handlers.Handler(fake).get_campaign("nope")
    assert resp.status == 404
    assert resp.body == {
        "type": "/problems/campaign_missing",
        "title": "campaign missing",
        "status": 404,
        "detail": "no campaign 'nope'",
    }


def test_a_conflict_is_409() -> None:
    fake = FakeCampaignClient(error=errors.conflict("duplicate_slug", "slug spring-sale already in c1"))
    resp = handlers.Handler(fake).add_link(
        "c1", json.dumps({"slug": "spring-sale", "target_url": "https://x.com"})
    )
    assert resp.status == 409
    assert resp.body["type"] == "/problems/duplicate_slug"
    assert resp.body["detail"] == "slug spring-sale already in c1"


def test_an_infrastructure_failure_is_503_and_leaks_nothing() -> None:
    fake = FakeCampaignClient(error=errors.InfraError("storage unavailable loading 'c1'"))
    resp = handlers.Handler(fake).get_campaign("c1")
    assert resp.body == {
        "type": "/problems/unavailable",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "please retry",
    }
    assert resp.status == 503


def test_an_unexpected_failure_is_500_and_leaks_nothing() -> None:
    fake = FakeCampaignClient(error=RuntimeError("a stack trace nobody should see"))
    resp = handlers.Handler(fake).get_campaign("c1")
    assert resp.body == {
        "type": "/problems/internal",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "unexpected error",
    }
    assert resp.status == 500


def test_getting_a_campaign_answers_200_with_its_links() -> None:
    fake = FakeCampaignClient(
        view=client.CampaignView(campaign_id="c1", links=("alpha-one", "beta-two"))
    )
    resp = handlers.Handler(fake).get_campaign("c1")
    assert resp.status == 200
    assert resp.body == {"id": "c1", "links": ["alpha-one", "beta-two"]}


def test_getting_a_campaign_hands_the_client_the_path_id() -> None:
    fake = FakeCampaignClient()
    handlers.Handler(fake).get_campaign("c9")
    req = fake.requests[0]
    assert isinstance(req, client.GetCampaignRequest)
    assert req.campaign_id == "c9"


def test_adding_a_link_answers_200_and_hands_the_client_the_body() -> None:
    fake = FakeCampaignClient()
    resp = handlers.Handler(fake).add_link(
        "c1", json.dumps({"slug": "spring-sale", "target_url": "https://x.com"})
    )
    assert resp.status == 200
    assert resp.body == {"status": "added"}
    req = fake.requests[0]
    assert isinstance(req, client.AddLinkRequest)
    assert (req.campaign_id, req.slug, req.target_url) == (
        "c1",
        "spring-sale",
        "https://x.com",
    )


def test_adding_a_link_with_a_missing_slug_is_400() -> None:
    fake = FakeCampaignClient()
    resp = handlers.Handler(fake).add_link("c1", json.dumps({"target_url": "https://x.com"}))
    assert resp.status == 400
    assert resp.body["detail"] == "expected a string field"
    assert fake.requests == []


def test_deactivating_a_link_answers_200_and_hands_the_client_the_slug() -> None:
    fake = FakeCampaignClient()
    resp = handlers.Handler(fake).deactivate_link("c1", "spring-sale")
    assert resp.status == 200
    assert resp.body == {"status": "deactivated"}
    req = fake.requests[0]
    assert isinstance(req, client.DeactivateLinkRequest)
    assert (req.campaign_id, req.slug) == ("c1", "spring-sale")
