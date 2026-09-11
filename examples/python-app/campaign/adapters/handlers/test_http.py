from __future__ import annotations

import pytest
import tesser.testing as ts

import campaign.adapters.handlers as handlers
import campaign.client as client
import protocol as protocol


@ts.fake
class FakeCampaignClientScripted(client.CampaignClient):

    def __init__(
        self,
        *views: client.CampaignView,
        resolved: str = "",
        error: Exception | None = None,
    ) -> None:
        self.pending = list(views)
        self.resolved = resolved
        self.error = error
        self.requests: list[object] = []

    def create_campaign(
        self, create_campaign_request: client.CreateCampaignRequest
    ) -> client.CampaignView:
        self.requests.append(create_campaign_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def add_link(self, add_link_request: client.AddLinkRequest) -> client.CampaignView:
        self.requests.append(add_link_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def deactivate_link(
        self, deactivate_link_request: client.DeactivateLinkRequest
    ) -> client.CampaignView:
        self.requests.append(deactivate_link_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def get_campaign(
        self, get_campaign_request: client.GetCampaignRequest
    ) -> client.CampaignView:
        self.requests.append(get_campaign_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def resolve(self, resolve_request: client.ResolveRequest) -> client.ResolveResponse:
        self.requests.append(resolve_request)
        if self.error is not None:
            raise self.error
        return client.ResolveResponse(target_url=self.resolved)

    def list_links(
        self, list_links_request: client.ListLinksRequest
    ) -> client.ListLinksResponse:
        raise AssertionError("list_links is not part of the HTTP surface")


def test_create_campaign_answers_201_with_the_campaign_payload() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    http_response = http_handler.create_campaign(
        protocol.HttpRequest(
            "POST", "/", {}, {}, {}, b'{"budget": {"amount": "100.00", "currency": "USD"}}'
        )
    )

    assert http_response.status_code == 201
    assert http_response.json_body() == {
        "campaign_id": "0123456789abcdef",
        "budget": {"amount": "100.00", "currency": "USD"},
        "links": [],
    }


def test_create_campaign_answers_json() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    http_response = http_handler.create_campaign(
        protocol.HttpRequest(
            "POST", "/", {}, {}, {}, b'{"budget": {"amount": "100.00", "currency": "USD"}}'
        )
    )

    assert http_response.headers["Content-Type"] == "application/json"


def test_create_campaign_forwards_the_budget_fields_it_read() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "250.00", "EUR", ())
    )
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    http_handler.create_campaign(
        protocol.HttpRequest(
            "POST", "/", {}, {}, {}, b'{"budget": {"amount": "250.00", "currency": "EUR"}}'
        )
    )

    request = fake_campaign_client_scripted.requests[0]
    assert isinstance(request, client.CreateCampaignRequest)
    assert request.budget_amount == "250.00"
    assert request.budget_currency == "EUR"


def test_create_campaign_refuses_a_budget_that_is_not_an_object() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted()
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    with pytest.raises(protocol.BadRequest):
        http_handler.create_campaign(protocol.HttpRequest("POST", "/", {}, {}, {}, b'{"budget": "100.00"}'))

    assert fake_campaign_client_scripted.requests == []


def test_create_campaign_refuses_a_budget_amount_that_is_not_a_string() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted()
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    with pytest.raises(protocol.BadRequest):
        http_handler.create_campaign(
            protocol.HttpRequest("POST", "/", {}, {}, {}, b'{"budget": {"amount": 100, "currency": "USD"}}')
        )

    assert fake_campaign_client_scripted.requests == []


def test_create_campaign_refuses_a_body_that_is_not_json() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted()
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    with pytest.raises(protocol.BadRequest):
        http_handler.create_campaign(protocol.HttpRequest("POST", "/", {}, {}, {}, b"not json"))

    assert fake_campaign_client_scripted.requests == []


def test_add_link_answers_200_with_the_links_of_the_campaign() -> None:
    campaign_view = client.CampaignView(
        "0123456789abcdef",
        "100.00",
        "USD",
        (client.LinkView("promo", "https://ok.example/x", "active"),),
    )
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(campaign_view))

    http_response = http_handler.add_link(
        protocol.HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "promo",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    assert http_response.status_code == 200
    assert http_response.json_body()["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "status": "active"}
    ]


def test_add_link_forwards_the_three_fields_it_read() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    http_handler.add_link(
        protocol.HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "promo",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    request = fake_campaign_client_scripted.requests[0]
    assert isinstance(request, client.AddLinkRequest)
    assert request.campaign_id == "0123456789abcdef"
    assert request.slug == "promo"
    assert request.target_url == "https://ok.example/x"


def test_add_link_refuses_a_body_with_a_missing_field() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted()
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    with pytest.raises(protocol.BadRequest):
        http_handler.add_link(
            protocol.HttpRequest("POST", "/", {}, {}, {}, b'{"campaign_id": "0123456789abcdef"}')
        )

    assert fake_campaign_client_scripted.requests == []


def test_deactivate_link_answers_200_with_the_link_reported_inactive() -> None:
    campaign_view = client.CampaignView(
        "0123456789abcdef",
        "100.00",
        "USD",
        (client.LinkView("promo", "https://ok.example/x", "inactive"),),
    )
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(campaign_view))

    http_response = http_handler.deactivate_link(
        protocol.HttpRequest(
            "POST", "/", {}, {}, {}, b'{"campaign_id": "0123456789abcdef", "slug": "promo"}'
        )
    )

    assert http_response.status_code == 200
    assert http_response.json_body()["links"] == [
        {"slug": "promo", "target_url": "https://ok.example/x", "status": "inactive"}
    ]


def test_deactivate_link_forwards_the_campaign_and_slug_it_read() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    http_handler.deactivate_link(
        protocol.HttpRequest(
            "POST", "/", {}, {}, {}, b'{"campaign_id": "0123456789abcdef", "slug": "promo"}'
        )
    )

    request = fake_campaign_client_scripted.requests[0]
    assert isinstance(request, client.DeactivateLinkRequest)
    assert request.campaign_id == "0123456789abcdef"
    assert request.slug == "promo"


def test_get_campaign_reads_the_id_off_the_path() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(
        client.CampaignView("0123456789abcdef", "100.00", "USD", ())
    )
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    http_response = http_handler.get_campaign(
        protocol.HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b"")
    )

    assert http_response.status_code == 200
    request = fake_campaign_client_scripted.requests[0]
    assert isinstance(request, client.GetCampaignRequest)
    assert request.campaign_id == "0123456789abcdef"


def test_get_campaign_refuses_a_request_with_no_campaign_id_on_the_path() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted()
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    with pytest.raises(protocol.BadRequest):
        http_handler.get_campaign(protocol.HttpRequest("GET", "/", {}, {}, {}, b""))

    assert fake_campaign_client_scripted.requests == []


def test_resolve_answers_a_redirect_to_the_target() -> None:
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(resolved="https://ok.example/x"))

    http_response = http_handler.resolve(protocol.HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))

    assert http_response.status_code == 302
    assert http_response.headers["Location"] == "https://ok.example/x"
    assert http_response.body == b""


def test_resolve_refuses_a_target_carrying_a_control_character() -> None:
    http_handler = handlers.HttpHandler(
        FakeCampaignClientScripted(resolved="https://ok.example/\r\nX-Injected: yes")
    )

    with pytest.raises(protocol.BadRequest):
        http_handler.resolve(protocol.HttpRequest("GET", "/", {"slug": "promo"}, {}, {}, b""))


def test_resolve_refuses_a_request_with_no_slug_on_the_path() -> None:
    fake_campaign_client_scripted = FakeCampaignClientScripted(resolved="https://ok.example/x")
    http_handler = handlers.HttpHandler(fake_campaign_client_scripted)

    with pytest.raises(protocol.BadRequest):
        http_handler.resolve(protocol.HttpRequest("GET", "/", {}, {}, {}, b""))

    assert fake_campaign_client_scripted.requests == []


def test_a_rejection_is_422_carrying_the_contexts_code_and_wording() -> None:
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(error=client.Rejected("invalid_slug", "slug is malformed")))

    http_response = http_handler.add_link(
        protocol.HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "BAD",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    assert http_response.status_code == 422
    assert http_response.json_body() == {
        "type": "/problems/invalid_slug",
        "detail": "slug is malformed",
    }


def test_a_missing_campaign_is_404_carrying_the_contexts_code() -> None:
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(error=client.Missing("campaign_missing", "no campaign with id 'x'")))

    http_response = http_handler.add_link(
        protocol.HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "BAD",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    assert http_response.status_code == 404
    assert http_response.json_body()["type"] == "/problems/campaign_missing"


def test_a_conflict_is_409_carrying_the_contexts_code() -> None:
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(error=client.Conflict("duplicate_slug", "slug 'promo' already exists")))

    http_response = http_handler.add_link(
        protocol.HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "BAD",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    assert http_response.status_code == 409
    assert http_response.json_body()["type"] == "/problems/duplicate_slug"


def test_an_unavailable_dependency_is_503_in_the_contexts_words() -> None:
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(error=client.Unavailable("the campaign store is unavailable")))

    http_response = http_handler.get_campaign(
        protocol.HttpRequest("GET", "/", {"campaign_id": "0123456789abcdef"}, {}, {}, b"")
    )

    assert http_response.status_code == 503
    assert http_response.json_body() == {
        "type": "/problems/unavailable",
        "detail": "the campaign store is unavailable",
    }


def test_an_unreadable_record_is_503_and_leaks_nothing() -> None:
    http_handler = handlers.HttpHandler(FakeCampaignClientScripted(error=client.Unreadable("stored campaign 'x' cannot be read back")))

    http_response = http_handler.add_link(
        protocol.HttpRequest(
            "POST",
            "/",
            {},
            {},
            {},
            b'{"campaign_id": "0123456789abcdef", "slug": "BAD",'
            b' "target_url": "https://ok.example/x"}',
        )
    )

    assert http_response.status_code == 503
    assert http_response.json_body() == {
        "type": "/problems/unavailable",
        "detail": "a dependency is unavailable; please retry",
    }


def test_a_failure_the_context_never_declared_leaves_the_handler() -> None:
    http_handler = handlers.HttpHandler(
        FakeCampaignClientScripted(error=RuntimeError("a stack trace nobody should see"))
    )

    with pytest.raises(RuntimeError):
        http_handler.add_link(
            protocol.HttpRequest(
                "POST",
                "/",
                {},
                {},
                {},
                b'{"campaign_id": "0123456789abcdef", "slug": "BAD",'
                b' "target_url": "https://ok.example/x"}',
            )
        )
