from __future__ import annotations

import typing

import tesser.adapters as ts

import campaign.client as client
import protocol as protocol

_CREATE_USAGE: typing.Final[str] = "usage: create-campaign <budget_amount> <currency>"
_ADD_USAGE: typing.Final[str] = "usage: add-link <campaign_id> <slug> <target_url>"
_DEACTIVATE_USAGE: typing.Final[str] = "usage: deactivate-link <campaign_id> <slug>"


class CliHandler(ts.Handler):
    def __init__(self, campaign_client: client.CampaignClient) -> None:
        self._campaign_client = campaign_client

    def create_campaign(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        amount = cli_request.arg(0, "budget_amount", _CREATE_USAGE)
        currency = cli_request.arg(1, "currency", _CREATE_USAGE)
        cli_request.no_extra_args(2, _CREATE_USAGE)
        try:
            create_campaign_response = self._campaign_client.create_campaign(
                client.CreateCampaignRequest(budget_amount=amount, budget_currency=currency)
            )
        except client.ERRORS as error:
            match error:
                case client.CampaignRejected():
                    return protocol.CliResponse(
                        2, stdout="", stderr=f"[{error.code}] {error.message}"
                    )
                case client.CampaignNotFound():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[campaign_not_found] {error.message}"
                    )
                case client.LinkNotFound():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[link_not_found] {error.message}"
                    )
                case client.SlugTaken():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[slug_taken] {error.message}"
                    )
                case client.TargetBlocked():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[target_blocked] {error.message}"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse.ok(
            f"created campaign {create_campaign_response.campaign.campaign_id} "
            f"with budget {create_campaign_response.campaign.budget_amount} {create_campaign_response.campaign.budget_currency}"
        )

    def add_link(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        campaign_id = cli_request.arg(0, "campaign_id", _ADD_USAGE)
        slug = cli_request.arg(1, "slug", _ADD_USAGE)
        target_url = cli_request.arg(2, "target_url", _ADD_USAGE)
        cli_request.no_extra_args(3, _ADD_USAGE)
        try:
            add_link_response = self._campaign_client.add_link(
                client.AddLinkRequest(campaign_id=campaign_id, slug=slug, target_url=target_url)
            )
        except client.ERRORS as error:
            match error:
                case client.CampaignRejected():
                    return protocol.CliResponse(
                        2, stdout="", stderr=f"[{error.code}] {error.message}"
                    )
                case client.CampaignNotFound():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[campaign_not_found] {error.message}"
                    )
                case client.LinkNotFound():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[link_not_found] {error.message}"
                    )
                case client.SlugTaken():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[slug_taken] {error.message}"
                    )
                case client.TargetBlocked():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[target_blocked] {error.message}"
                    )
                case _ as never:
                    typing.assert_never(never)
        return protocol.CliResponse.ok(f"campaign {add_link_response.campaign.campaign_id} now has {len(add_link_response.campaign.links)} link(s)")

    def deactivate_link(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        campaign_id = cli_request.arg(0, "campaign_id", _DEACTIVATE_USAGE)
        slug = cli_request.arg(1, "slug", _DEACTIVATE_USAGE)
        cli_request.no_extra_args(2, _DEACTIVATE_USAGE)
        try:
            deactivate_link_response = self._campaign_client.deactivate_link(
                client.DeactivateLinkRequest(campaign_id=campaign_id, slug=slug)
            )
        except client.ERRORS as error:
            match error:
                case client.CampaignRejected():
                    return protocol.CliResponse(
                        2, stdout="", stderr=f"[{error.code}] {error.message}"
                    )
                case client.CampaignNotFound():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[campaign_not_found] {error.message}"
                    )
                case client.LinkNotFound():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[link_not_found] {error.message}"
                    )
                case client.SlugTaken():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[slug_taken] {error.message}"
                    )
                case client.TargetBlocked():
                    return protocol.CliResponse(
                        1, stdout="", stderr=f"[target_blocked] {error.message}"
                    )
                case _ as never:
                    typing.assert_never(never)
        active = sum(1 for link in deactivate_link_response.campaign.links if link.status == "active")
        return protocol.CliResponse.ok(f"campaign {deactivate_link_response.campaign.campaign_id} now has {active} active link(s)")
