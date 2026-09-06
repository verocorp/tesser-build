from __future__ import annotations

import secrets

import tesser.adapters as ts

import campaign.application.ports as ports


class SecretsCampaignIdentity(ts.Gateway):

    def issue(
        self, issue_campaign_identity_request: ports.IssueCampaignIdentityRequest
    ) -> ports.IssueCampaignIdentityResponse:
        campaign_id = secrets.token_hex(8)
        return ports.IssueCampaignIdentityResponse(campaign_id=campaign_id)
