from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.handlers.http as http
import campaign.client.client as campaign_client
from tesser.errors import DomainError, invalid
from protocol.http import BadRequest, HttpRequest


@ts.fake
class FakeCampaignClientScripted(campaign_client.Client):

    def __init__(
        self,
        *views: campaign_client.CampaignView,
        resolved: str = "",
        error: Exception | None = None,
    ) -> None:
        self.pending = list(views)
        self.resolved = resolved
        self.error = error
        self.requests: list[object] = []

    def _next(self, request: object) -> campaign_client.CampaignView:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def create_campaign(
        self, req: campaign_client.CreateCampaignRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def add_link(self, req: campaign_client.AddLinkRequest) -> campaign_client.CampaignView:
        return self._next(req)

    def deactivate_link(
        self, req: campaign_client.DeactivateLinkRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def get_campaign(
        self, req: campaign_client.GetCampaignRequest
    ) -> campaign_client.CampaignView:
        return self._next(req)

    def resolve(self, req: campaign_client.ResolveRequest) -> campaign_client.ResolveResponse:
        self.requests.append(req)
        if self.error is not None:
            raise self.error
        return campaign_client.ResolveResponse(target_url=self.resolved)

    def list_links(
        self, req: campaign_client.ListLinksRequest
    ) -> campaign_client.ListLinksResponse:
        raise AssertionError("list_links is not part of the HTTP surface")


def test_create_campaign_answers_201_with_the_campaign_payload() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    handler = http.Handler(client)

    resp = handler.create_campaign(
        HttpRequest(
            "POST", "/", {}, {}, {}, b'{"budget": {"amount": "100.00", "currency": "USD"}}'
        )
    )

    assert resp.status_code == 201
    assert resp.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [],
    }


def test_create_campaign_answers_json() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    handler = http.Handler(client)

    resp = handler.create_campaign(
        HttpRequest(
            "POST", "/", {}, {}, {}, b'{"budget": {"amount": "100.00", "currency": "USD"}}'
        )
    )

    assert resp.headers["Content-Type"] == "application/json"


def test_create_campaign_forwards_the_budget_fields_it_read() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "250.00", "EUR", ())
    )
    handler = http.Handler(client)

    handler.create_campaign(
        HttpRequest(
            "POST", "/", {}, {}, {}, b'{"budget": {"amount": "250.00", "currency": "EUR"}}'
        )
    )

    request = client.requests[0]
    assert isinstance(request, campaign_client.CreateCampaignRequest)
    assert request.budget_amount == "250.00"
    assert request.budget_currency == "EUR"


def test_create_campaign_refuses_a_budget_that_is_not_an_object() -> None:
    client = FakeCampaignClientScripted()
    handler = http.Handler(client)

    with pytest.raises(BadRequest):
        handler.create_campaign(HttpRequest("POST", "/", {}, {}, {}, b'{"budget": "100.00"}'))

    assert client.requests == []


def test_create_campaign_refuses_a_budget_amount_that_is_not_a_string() -> None:
    client = FakeCampaignClientScripted()
    handler = http.Handler(client)

    with pytest.raises(BadRequest):
        handler.create_campaign(
            HttpRequest("POST", "/", {}, {}, {}, b'{"budget": {"amount": 100, "currency": "USD"}}')
        )

    assert client.requests == []


def test_create_campaign_refuses_a_body_that_is_not_json() -> None:
    client = FakeCampaignClientScripted()
    handler = http.Handler(client)

    with pytest.raises(BadRequest):
        handler.create_campaign(HttpRequest("POST", "/", {}, {}, {}, b"not json"))

    assert client.requests == []


def test_add_link_answers_200_with_the_links_of_the_campaign() -> None:
    view = campaign_client.CampaignView(
        "0123456789abcdef",
        "100.00",
        "USD",
        (campaign_client.LinkView("promo", "https://ok.example/x", True),),
    )
    handler = http.Handler(FakeCampaignClientScripted(view))

    resp = handler.add_link(
        HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "promo",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    assert resp.status_code == 200
    assert resp.json_body()["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "active": True}
    ]


def test_add_link_forwards_the_three_fields_it_read() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    handler = http.Handler(client)

    handler.add_link(
        HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "promo",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    request = client.requests[0]
    assert isinstance(request, campaign_client.AddLinkRequest)
    assert request.campaign_id == "0123456789abcdef"
    assert request.slug == "promo"
    assert request.target_url == "https://ok.example/x"


def test_add_link_refuses_a_body_with_a_missing_field() -> None:
    client = FakeCampaignClientScripted()
    handler = http.Handler(client)

    with pytest.raises(BadRequest):
        handler.add_link(
            HttpRequest("POST", "/", {}, {}, {}, b'{"campaign_id": "0123456789abcdef"}')
        )

    assert client.requests == []


def test_deactivate_link_answers_200_with_the_link_reported_inactive() -> None:
    view = campaign_client.CampaignView(
        "0123456789abcdef",
        "100.00",
        "USD",
        (campaign_client.LinkView("promo", "https://ok.example/x", False),),
    )
    handler = http.Handler(FakeCampaignClientScripted(view))

    resp = handler.deactivate_link(
        HttpRequest(
            "POST", "/", {}, {}, {}, b'{"campaign_id": "0123456789abcdef", "slug": "promo"}'
        )
    )

    assert resp.status_code == 200
    assert resp.json_body()["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "active": False}
    ]


def test_deactivate_link_forwards_the_campaign_and_slug_it_read() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    handler = http.Handler(client)

    handler.deactivate_link(
        HttpRequest(
            "POST", "/", {}, {}, {}, b'{"campaign_id": "0123456789abcdef", "slug": "promo"}'
        )
    )

    request = client.requests[0]
    assert isinstance(request, campaign_client.DeactivateLinkRequest)
    assert request.campaign_id == "0123456789abcdef"
    assert request.slug == "promo"


def test_get_campaign_reads_the_id_off_the_path() -> None:
    client = FakeCampaignClientScripted(
        campaign_client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    handler = http.Handler(client)

    resp = handler.get_campaign(
        HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b"")
    )

    assert resp.status_code == 200
    request = client.requests[0]
    assert isinstance(request, campaign_client.GetCampaignRequest)
    assert request.campaign_id == "0123456789abcdef"


def test_get_campaign_refuses_a_request_with_no_campaign_id_on_the_path() -> None:
    client = FakeCampaignClientScripted()
    handler = http.Handler(client)

    with pytest.raises(BadRequest):
        handler.get_campaign(HttpRequest("GET", "/", {}, {}, {}, b""))

    assert client.requests == []


def test_resolve_answers_a_redirect_to_the_target() -> None:
    handler = http.Handler(FakeCampaignClientScripted(resolved="https://ok.example/x"))

    resp = handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))

    assert resp.status_code == 302
    assert resp.headers["Location"] == "https://ok.example/x"
    assert resp.body == b""


def test_resolve_refuses_a_target_carrying_a_control_character() -> None:
    handler = http.Handler(
        FakeCampaignClientScripted(resolved="https://ok.example/\r\nX-Injected: yes")
    )

    with pytest.raises(BadRequest):
        handler.resolve(HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))


def test_resolve_refuses_a_request_with_no_slug_on_the_path() -> None:
    client = FakeCampaignClientScripted(resolved="https://ok.example/x")
    handler = http.Handler(client)

    with pytest.raises(BadRequest):
        handler.resolve(HttpRequest("GET", "/", {}, {}, {}, b""))

    assert client.requests == []


def test_a_client_rejection_travels_out_of_the_handler_unconverted() -> None:
    client = FakeCampaignClientScripted(error=invalid("invalid_slug", "slug is malformed"))
    handler = http.Handler(client)

    with pytest.raises(DomainError) as caught:
        handler.add_link(
            HttpRequest(
                "POST",
                "/",
                {},
                {},
                {},
                b'{"campaign_id": "0123456789abcdef", "slug": "BAD",'
                b' "target_url": "https://ok.example/x"}',
            )
        )

    assert caught.value.code == "invalid_slug"
