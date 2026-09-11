from __future__ import annotations

import json

import tesser.testing as ts

import campaign.adapters.handlers as handlers
import campaign.client as client


@ts.fake
class FakeCampaignClient(client.CampaignClient):

    def __init__(
        self,
        view: client.CampaignView | None = None,
        error: Exception | None = None,
    ) -> None:
        self.view = view
        self.error = error
        self.requests: list[object] = []

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CampaignView:
        self.requests.append(create_campaign_request)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        self.requests.append(get_campaign_request)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        self.requests.append(add_link_request)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        self.requests.append(deactivate_link_request)
        if self.error is not None:
            raise self.error
        if self.view is None:
            return client.CampaignView(campaign_id="c1", links=())
        return self.view


def test_creating_a_campaign_answers_201_with_the_id() -> None:
    response = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    assert response.status == 201
    assert response.body == {"id": "c1"}


def test_creating_a_campaign_hands_the_client_the_parsed_body() -> None:
    fake_campaign_client = FakeCampaignClient()
    handlers.Handler(fake_campaign_client).create_campaign(
        "c1",
        json.dumps(
            {
                "window": {"start": "2026-01-01", "end": "2026-02-01"},
                "links": [{"slug": "spring-sale", "target_url": "https://x.com"}],
            }
        ),
    )
    req = fake_campaign_client.requests[0]
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
    fake_campaign_client = FakeCampaignClient()
    response = handlers.Handler(fake_campaign_client).create_campaign("c1", "{not json")
    assert response.status == 400
    assert response.body["type"] == "/problems/malformed_request"
    assert response.body["title"] == "Bad Request"
    assert response.body["status"] == 400
    assert str(response.body["detail"]).startswith("malformed JSON: ")
    assert fake_campaign_client.requests == []


def test_a_json_array_body_is_400_because_the_top_level_must_be_an_object() -> None:
    fake_campaign_client = FakeCampaignClient()
    response = handlers.Handler(fake_campaign_client).create_campaign("c1", "[1, 2]")
    assert response.status == 400
    assert response.body["detail"] == "expected a JSON object"
    assert fake_campaign_client.requests == []


def test_a_json_scalar_body_is_400_because_the_top_level_must_be_an_object() -> None:
    fake_campaign_client = FakeCampaignClient()
    response = handlers.Handler(fake_campaign_client).create_campaign("c1", "7")
    assert response.status == 400
    assert response.body["detail"] == "expected a JSON object"
    assert fake_campaign_client.requests == []


def test_a_window_that_is_not_an_object_is_400_naming_the_field() -> None:
    response = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1", json.dumps({"window": "2026-01-01", "links": []})
    )
    assert response.status == 400
    assert response.body["detail"] == "'window' must be an object"


def test_links_that_are_not_an_array_is_400_naming_the_field() -> None:
    response = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps({"window": {"start": "2026-01-01", "end": "2026-02-01"}, "links": {}}),
    )
    assert response.status == 400
    assert response.body["detail"] == "'links' must be an array"


def test_a_link_entry_that_is_not_an_object_is_400() -> None:
    response = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps(
            {"window": {"start": "2026-01-01", "end": "2026-02-01"}, "links": ["nope"]}
        ),
    )
    assert response.status == 400
    assert response.body["detail"] == "'link' must be an object"


def test_a_window_start_that_is_not_a_string_is_400() -> None:
    response = handlers.Handler(FakeCampaignClient()).create_campaign(
        "c1",
        json.dumps({"window": {"start": 20260101, "end": "2026-02-01"}, "links": []}),
    )
    assert response.status == 400
    assert response.body["detail"] == "expected a string field"


def test_a_validation_failure_is_422_carrying_the_code_title_and_field() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Rejected(
            client.Rejection("bad_slug", "invalid slug 'BAD'", "links[0].slug", ())
        )
    )
    response = handlers.Handler(fake_campaign_client).create_campaign(
        "c1", json.dumps({"window": {"start": "2026-01-01", "end": "2026-02-01"}, "links": []})
    )
    assert response.body == {
        "type": "/problems/bad_slug",
        "title": "bad slug",
        "status": 422,
        "detail": "invalid slug 'BAD'",
        "field": "links[0].slug",
    }
    assert response.status == 422


def test_an_aggregated_validation_failure_lists_every_invalid_param() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Rejected(
            client.Rejection(
                "validation_failed",
                "one or more fields are invalid",
                "",
                (
                    client.Problem("bad_slug", "slug", "invalid slug 'BAD'"),
                    client.Problem(
                        "bad_target_url", "target_url", "invalid target url 'ftp://x'"
                    ),
                ),
            )
        )
    )
    response = handlers.Handler(fake_campaign_client).add_link(
        "c1", json.dumps({"slug": "BAD", "target_url": "ftp://x"})
    )
    assert response.status == 422
    assert response.body["invalid-params"] == [
        {"name": "slug", "code": "bad_slug", "reason": "invalid slug 'BAD'"},
        {"name": "target_url", "code": "bad_target_url", "reason": "invalid target url 'ftp://x'"},
    ]
    assert "field" not in response.body


def test_a_missing_campaign_is_404() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Missing("campaign_missing", "no campaign 'nope'")
    )
    response = handlers.Handler(fake_campaign_client).get_campaign("nope")
    assert response.status == 404
    assert response.body == {
        "type": "/problems/campaign_missing",
        "title": "campaign missing",
        "status": 404,
        "detail": "no campaign 'nope'",
    }


def test_a_conflict_is_409() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Conflict("duplicate_slug", "slug spring-sale already in c1")
    )
    response = handlers.Handler(fake_campaign_client).add_link(
        "c1", json.dumps({"slug": "spring-sale", "target_url": "https://x.com"})
    )
    assert response.status == 409
    assert response.body["type"] == "/problems/duplicate_slug"
    assert response.body["detail"] == "slug spring-sale already in c1"


def test_an_unavailable_store_is_503_and_leaks_nothing() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Unavailable("campaign storage cannot answer for 'c1'")
    )
    response = handlers.Handler(fake_campaign_client).get_campaign("c1")
    assert response.body == {
        "type": "/problems/unavailable",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "please retry",
    }
    assert response.status == 503


def test_an_unexpected_failure_is_500_and_leaks_nothing() -> None:
    fake_campaign_client = FakeCampaignClient(error=RuntimeError("a stack trace nobody should see"))
    response = handlers.Handler(fake_campaign_client).get_campaign("c1")
    assert response.body == {
        "type": "/problems/internal",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "unexpected error",
    }
    assert response.status == 500


def test_getting_a_campaign_answers_200_with_its_links() -> None:
    fake_campaign_client = FakeCampaignClient(
        view=client.CampaignView(campaign_id="c1", links=("alpha-one", "beta-two"))
    )
    response = handlers.Handler(fake_campaign_client).get_campaign("c1")
    assert response.status == 200
    assert response.body == {"id": "c1", "links": ["alpha-one", "beta-two"]}


def test_getting_a_campaign_hands_the_client_the_path_id() -> None:
    fake_campaign_client = FakeCampaignClient()
    handlers.Handler(fake_campaign_client).get_campaign("c9")
    req = fake_campaign_client.requests[0]
    assert isinstance(req, client.GetCampaignRequest)
    assert req.campaign_id == "c9"


def test_adding_a_link_answers_200_and_hands_the_client_the_body() -> None:
    fake_campaign_client = FakeCampaignClient()
    response = handlers.Handler(fake_campaign_client).add_link(
        "c1", json.dumps({"slug": "spring-sale", "target_url": "https://x.com"})
    )
    assert response.status == 200
    assert response.body == {"status": "added"}
    req = fake_campaign_client.requests[0]
    assert isinstance(req, client.AddLinkRequest)
    assert (req.campaign_id, req.slug, req.target_url) == (
        "c1",
        "spring-sale",
        "https://x.com",
    )


def test_adding_a_link_with_a_missing_slug_is_400() -> None:
    fake_campaign_client = FakeCampaignClient()
    response = handlers.Handler(fake_campaign_client).add_link("c1", json.dumps({"target_url": "https://x.com"}))
    assert response.status == 400
    assert response.body["detail"] == "expected a string field"
    assert fake_campaign_client.requests == []


def test_deactivating_a_link_answers_200_and_hands_the_client_the_slug() -> None:
    fake_campaign_client = FakeCampaignClient()
    response = handlers.Handler(fake_campaign_client).deactivate_link("c1", "spring-sale")
    assert response.status == 200
    assert response.body == {"status": "deactivated"}
    req = fake_campaign_client.requests[0]
    assert isinstance(req, client.DeactivateLinkRequest)
    assert (req.campaign_id, req.slug) == ("c1", "spring-sale")


def test_an_unreadable_record_is_503_and_leaks_nothing() -> None:
    fake_campaign_client = FakeCampaignClient(
        error=client.Unreadable("corrupted campaign record 'c1': [bad_slug] bad")
    )
    response = handlers.Handler(fake_campaign_client).get_campaign("c1")
    assert response.body == {
        "type": "/problems/unavailable",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "please retry",
    }
    assert response.status == 503
