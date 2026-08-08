from __future__ import annotations

import tesser.adapters as ts

from campaign.client import (
    AddLinkRequest,
    CampaignView,
    Client,
    CreateCampaignRequest,
    DeactivateLinkRequest,
    GetCampaignRequest,
    ResolveRequest,
)
from httpwire import HttpRequest, JSONObject, Response, object_field, string_field


class Handler(ts.Handler):
    def __init__(self, client: Client) -> None:
        self._client = client

    def create_campaign(self, req: HttpRequest) -> Response:
        def run() -> Response:
            body = req.json_body()
            budget = object_field(body.get("budget"))
            view = self._client.create_campaign(
                CreateCampaignRequest(
                    budget_amount=string_field(budget.get("amount")),
                    budget_currency=string_field(budget.get("currency")),
                )
            )
            return Response.json(201, _campaign_body(view))

        return Response.respond(run)

    def add_link(self, req: HttpRequest) -> Response:
        def run() -> Response:
            body = req.json_body()
            view = self._client.add_link(
                AddLinkRequest(
                    campaign_id=string_field(body.get("campaign_id")),
                    slug=string_field(body.get("slug")),
                    target_url=string_field(body.get("target_url")),
                )
            )
            return Response.json(200, _campaign_body(view))

        return Response.respond(run)

    def deactivate_link(self, req: HttpRequest) -> Response:
        def run() -> Response:
            body = req.json_body()
            view = self._client.deactivate_link(
                DeactivateLinkRequest(
                    campaign_id=string_field(body.get("campaign_id")),
                    slug=string_field(body.get("slug")),
                )
            )
            return Response.json(200, _campaign_body(view))

        return Response.respond(run)

    def get_campaign(self, req: HttpRequest) -> Response:
        def run() -> Response:
            view = self._client.get_campaign(
                GetCampaignRequest(campaign_id=req.path_param("campaign_id"))
            )
            return Response.json(200, _campaign_body(view))

        return Response.respond(run)

    def resolve(self, req: HttpRequest) -> Response:
        def run() -> Response:
            resp = self._client.resolve(ResolveRequest(slug=req.path_param("slug")))
            return Response.redirect(resp.target_url)

        return Response.respond(run)


@ts.function
def _campaign_body(view: CampaignView) -> JSONObject:
    return {
        "campaign_id": view.campaign_id,
        "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
        "links": [
            {"slug": link.slug, "target_url": link.target_url, "active": link.active}
            for link in view.links
        ],
    }
