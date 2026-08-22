from __future__ import annotations

import tesser.adapters as ts

import campaign.client.client as client
from protocol.http import BadRequest, HttpRequest, HttpResponse


class Handler(ts.Handler):
    def __init__(self, client: client.Client) -> None:
        self._client = client

    def create_campaign(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()
        budget = body.get("budget")
        if not isinstance(budget, dict):
            raise BadRequest("expected a JSON object field")
        amount = budget.get("amount")
        if not isinstance(amount, str):
            raise BadRequest("expected a string field")
        currency = budget.get("currency")
        if not isinstance(currency, str):
            raise BadRequest("expected a string field")
        view = self._client.create_campaign(
            client.CreateCampaignRequest(budget_amount=amount, budget_currency=currency)
        )
        return HttpResponse.json(201, {
            "campaign_id": view.campaign_id,
            "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in view.links
            ],
        })

    def add_link(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()
        campaign_id = body.get("campaign_id")
        if not isinstance(campaign_id, str):
            raise BadRequest("expected a string field")
        slug = body.get("slug")
        if not isinstance(slug, str):
            raise BadRequest("expected a string field")
        target_url = body.get("target_url")
        if not isinstance(target_url, str):
            raise BadRequest("expected a string field")
        view = self._client.add_link(
            client.AddLinkRequest(campaign_id=campaign_id, slug=slug, target_url=target_url)
        )
        return HttpResponse.json(200, {
            "campaign_id": view.campaign_id,
            "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in view.links
            ],
        })

    def deactivate_link(self, req: HttpRequest) -> HttpResponse:
        body = req.json_body()
        campaign_id = body.get("campaign_id")
        if not isinstance(campaign_id, str):
            raise BadRequest("expected a string field")
        slug = body.get("slug")
        if not isinstance(slug, str):
            raise BadRequest("expected a string field")
        view = self._client.deactivate_link(
            client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
        )
        return HttpResponse.json(200, {
            "campaign_id": view.campaign_id,
            "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in view.links
            ],
        })

    def get_campaign(self, req: HttpRequest) -> HttpResponse:
        view = self._client.get_campaign(
            client.GetCampaignRequest(campaign_id=req.path_param("campaign_id"))
        )
        return HttpResponse.json(200, {
            "campaign_id": view.campaign_id,
            "budget": {"amount": view.budget_amount, "currency": view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in view.links
            ],
        })

    def resolve(self, req: HttpRequest) -> HttpResponse:
        resp = self._client.resolve(client.ResolveRequest(slug=req.path_param("slug")))
        return HttpResponse.redirect(resp.target_url)
