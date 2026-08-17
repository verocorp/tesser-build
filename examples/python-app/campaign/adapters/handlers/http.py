from __future__ import annotations

import tesser.adapters as ts

import campaign.client.client as client
from protocol.http import HttpRequest, JSONObject, HttpResponse, object_field, string_field


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def create_campaign(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()
        budget = object_field(body.get("budget"))
        view = self._client.create_campaign(
            client.CreateCampaignRequest(
                budget_amount=string_field(budget.get("amount")),
                budget_currency=string_field(budget.get("currency")),
            )
        )
        return HttpResponse.json(201, _campaign_body(view))

    def add_link(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()
        view = self._client.add_link(
            client.AddLinkRequest(
                campaign_id=string_field(body.get("campaign_id")),
                slug=string_field(body.get("slug")),
                target_url=string_field(body.get("target_url")),
            )
        )
        return HttpResponse.json(200, _campaign_body(view))

    def deactivate_link(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()
        view = self._client.deactivate_link(
            client.DeactivateLinkRequest(
                campaign_id=string_field(body.get("campaign_id")),
                slug=string_field(body.get("slug")),
            )
        )
        return HttpResponse.json(200, _campaign_body(view))

    def get_campaign(self, req: HttpRequest) -> HttpResponse:
        view = self._client.get_campaign(
            client.GetCampaignRequest(campaign_id=req.path_param("campaign_id"))
        )
        return HttpResponse.json(200, _campaign_body(view))

    def resolve(self, req: HttpRequest) -> HttpResponse:
        resp = self._client.resolve(client.ResolveRequest(slug=req.path_param("slug")))
        return HttpResponse.redirect(resp.target_url)


@ts.do_not_use_function
def _campaign_body(view: client.CampaignView) -> JSONObject:
    return {
        "campaign_id": view.campaign_id,
        "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
        "links": [
            {"slug": link.slug, "target_url": link.target_url, "active": link.active}
            for link in view.links
        ],
    }
