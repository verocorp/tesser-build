from __future__ import annotations

import json

from campaign.client import (
    AddLinkRequest,
    CampaignView,
    Client,
    CreateCampaignRequest,
    DeactivateLinkRequest,
    GetCampaignRequest,
    ResolveRequest,
)
from httpwire import BadRequest, JSONObject, Response, respond


class Handler:
    def __init__(self, client: Client) -> None:
        self._client = client

    def create_campaign(self, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)
            budget = _obj(body.get("budget"))
            view = self._client.create_campaign(
                CreateCampaignRequest(
                    budget_amount=_str(budget.get("amount")),
                    budget_currency=_str(budget.get("currency")),
                )
            )
            return Response(201, _campaign_body(view))

        return respond(run)

    def add_link(self, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)
            view = self._client.add_link(
                AddLinkRequest(
                    campaign_id=_str(body.get("campaign_id")),
                    slug=_str(body.get("slug")),
                    target_url=_str(body.get("target_url")),
                )
            )
            return Response(200, _campaign_body(view))

        return respond(run)

    def deactivate_link(self, raw: str) -> Response:
        def run() -> Response:
            body = _parse(raw)
            view = self._client.deactivate_link(
                DeactivateLinkRequest(
                    campaign_id=_str(body.get("campaign_id")),
                    slug=_str(body.get("slug")),
                )
            )
            return Response(200, _campaign_body(view))

        return respond(run)

    def get_campaign(self, campaign_id: str) -> Response:
        def run() -> Response:
            view = self._client.get_campaign(GetCampaignRequest(campaign_id=campaign_id))
            return Response(200, _campaign_body(view))

        return respond(run)

    def resolve(self, slug: str) -> Response:
        def run() -> Response:
            resp = self._client.resolve(ResolveRequest(slug=slug))
            return Response(302, {"location": resp.target_url})

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


def _parse(raw: str) -> JSONObject:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BadRequest(f"malformed JSON: {e}") from e
    if not isinstance(data, dict):
        raise BadRequest("expected a JSON object")
    return data


def _obj(value: object) -> JSONObject:
    if not isinstance(value, dict):
        raise BadRequest("expected a JSON object field")
    return value


def _str(value: object) -> str:
    if not isinstance(value, str):
        raise BadRequest("expected a string field")
    return value
