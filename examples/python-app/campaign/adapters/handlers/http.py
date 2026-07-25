from __future__ import annotations

from campaign.client import (
    AddLinkRequest,
    CampaignView,
    Client,
    CreateCampaignRequest,
    DeactivateLinkRequest,
    GetCampaignRequest,
    ResolveRequest,
)
from httpwire import (
    HttpRequest,
    JSONObject,
    Response,
    object_field,
    path_param,
    redirect,
    respond,
    string_field,
)


class Handler:
    def __init__(self, client: Client) -> None:
        self._client = client

    def create_campaign(self, req: HttpRequest) -> Response:
        def run() -> Response:
            budget = object_field(req.body.get("budget"))
            view = self._client.create_campaign(
                CreateCampaignRequest(
                    budget_amount=string_field(budget.get("amount")),
                    budget_currency=string_field(budget.get("currency")),
                )
            )
            return Response(201, _campaign_body(view))

        return respond(run)

    def add_link(self, req: HttpRequest) -> Response:
        def run() -> Response:
            view = self._client.add_link(
                AddLinkRequest(
                    campaign_id=string_field(req.body.get("campaign_id")),
                    slug=string_field(req.body.get("slug")),
                    target_url=string_field(req.body.get("target_url")),
                )
            )
            return Response(200, _campaign_body(view))

        return respond(run)

    def deactivate_link(self, req: HttpRequest) -> Response:
        def run() -> Response:
            view = self._client.deactivate_link(
                DeactivateLinkRequest(
                    campaign_id=string_field(req.body.get("campaign_id")),
                    slug=string_field(req.body.get("slug")),
                )
            )
            return Response(200, _campaign_body(view))

        return respond(run)

    def get_campaign(self, req: HttpRequest) -> Response:
        def run() -> Response:
            view = self._client.get_campaign(
                GetCampaignRequest(campaign_id=path_param(req, "campaign_id"))
            )
            return Response(200, _campaign_body(view))

        return respond(run)

    def resolve(self, req: HttpRequest) -> Response:
        def run() -> Response:
            resp = self._client.resolve(ResolveRequest(slug=path_param(req, "slug")))
            return redirect(resp.target_url)

        return respond(run)


def _campaign_body(view: CampaignView) -> JSONObject:
    return {
        "campaign_id": view.campaign_id,
        "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
        "links": [
            {"slug": link.slug, "target_url": link.target_url, "active": link.active}
            for link in view.links
        ],
    }
