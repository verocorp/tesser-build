from __future__ import annotations

import campaign.adapters.gateways as gateways
import campaign.application.ports as ports


def test_an_issued_identity_is_sixteen_lowercase_hex_chars() -> None:
    secrets_campaign_identity = gateways.SecretsCampaignIdentity()
    issue_campaign_identity_response = secrets_campaign_identity.issue(
        ports.IssueCampaignIdentityRequest()
    )
    assert len(issue_campaign_identity_response.campaign_id) == 16
    assert all(
        ch in "0123456789abcdef" for ch in issue_campaign_identity_response.campaign_id
    )


def test_each_issue_returns_a_different_identity() -> None:
    secrets_campaign_identity = gateways.SecretsCampaignIdentity()
    first = secrets_campaign_identity.issue(ports.IssueCampaignIdentityRequest())
    second = secrets_campaign_identity.issue(ports.IssueCampaignIdentityRequest())
    assert first.campaign_id != second.campaign_id
