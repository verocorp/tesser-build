from __future__ import annotations

import typing

import tesser.adapters as ts

import campaign.client as client
import protocol as protocol


class HttpHandler(ts.Handler):
    def __init__(self, campaign_client: client.CampaignClient) -> None:
        self._campaign_client = campaign_client

    def create_campaign(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        body = http_request.json_body()
        budget = body.get("budget")
        if not isinstance(budget, dict):
            raise protocol.BadRequest("expected a JSON object field")
        amount = budget.get("amount")
        if not isinstance(amount, str):
            raise protocol.BadRequest("expected a string field")
        currency = budget.get("currency")
        if not isinstance(currency, str):
            raise protocol.BadRequest("expected a string field")
        try:
            campaign_view = self._campaign_client.create_campaign(
                client.CreateCampaignRequest(budget_amount=amount, budget_currency=currency)
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.code, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.code, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.code, error.message)
                case client.Unreadable():
                    return protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse.json(201, {
            "campaign_id": campaign_view.campaign_id,
            "budget": {"amount": campaign_view.budget_amount, "currency": campaign_view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in campaign_view.links
            ],
        })

    def add_link(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        body = http_request.json_body()
        campaign_id = body.get("campaign_id")
        if not isinstance(campaign_id, str):
            raise protocol.BadRequest("expected a string field")
        slug = body.get("slug")
        if not isinstance(slug, str):
            raise protocol.BadRequest("expected a string field")
        target_url = body.get("target_url")
        if not isinstance(target_url, str):
            raise protocol.BadRequest("expected a string field")
        try:
            campaign_view = self._campaign_client.add_link(
                client.AddLinkRequest(campaign_id=campaign_id, slug=slug, target_url=target_url)
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.code, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.code, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.code, error.message)
                case client.Unreadable():
                    return protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse.json(200, {
            "campaign_id": campaign_view.campaign_id,
            "budget": {"amount": campaign_view.budget_amount, "currency": campaign_view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in campaign_view.links
            ],
        })

    def deactivate_link(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        body = http_request.json_body()
        campaign_id = body.get("campaign_id")
        if not isinstance(campaign_id, str):
            raise protocol.BadRequest("expected a string field")
        slug = body.get("slug")
        if not isinstance(slug, str):
            raise protocol.BadRequest("expected a string field")
        try:
            campaign_view = self._campaign_client.deactivate_link(
                client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.code, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.code, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.code, error.message)
                case client.Unreadable():
                    return protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse.json(200, {
            "campaign_id": campaign_view.campaign_id,
            "budget": {"amount": campaign_view.budget_amount, "currency": campaign_view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in campaign_view.links
            ],
        })

    def get_campaign(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            campaign_view = self._campaign_client.get_campaign(
                client.GetCampaignRequest(campaign_id=http_request.path_param("campaign_id"))
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.code, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.code, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.code, error.message)
                case client.Unreadable():
                    return protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse.json(200, {
            "campaign_id": campaign_view.campaign_id,
            "budget": {"amount": campaign_view.budget_amount, "currency": campaign_view.budget_currency},
            "links": [
                {"slug": link.slug, "target_url": link.target_url, "status": link.status}
                for link in campaign_view.links
            ],
        })

    def resolve(self, http_request: protocol.HttpRequest) -> protocol.HttpResponse:
        try:
            resolve_response = self._campaign_client.resolve(
                client.ResolveRequest(slug=http_request.path_param("slug"))
            )
        except client.ERRORS as error:
            match error:
                case client.Rejected():
                    return protocol.HttpResponse.problem(422, error.code, error.message)
                case client.Missing():
                    return protocol.HttpResponse.problem(404, error.code, error.message)
                case client.Conflict():
                    return protocol.HttpResponse.problem(409, error.code, error.message)
                case client.Unreadable():
                    return protocol.HttpResponse.problem(
                        503, "unavailable", "a dependency is unavailable; please retry"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.HttpResponse.redirect(resolve_response.target_url)
