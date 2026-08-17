from __future__ import annotations

import secrets

import tesser.adapters as ts

import campaign.application.ports.campaign_identity as campaign_identity


class SecretsCampaignIdentity(ts.Gateway):

    def issue(
        self, request: campaign_identity.IssueCampaignIdentityRequest
    ) -> campaign_identity.IssueCampaignIdentityResponse:
        campaign_id = secrets.token_hex(8)
        return campaign_identity.IssueCampaignIdentityResponse(campaign_id=campaign_id)
