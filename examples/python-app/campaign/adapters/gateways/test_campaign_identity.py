from __future__ import annotations

import campaign.adapters.gateways.campaign_identity as campaign_identity
import campaign.application.ports.campaign_identity as port


def test_an_issued_identity_is_sixteen_lowercase_hex_chars() -> None:
    gateway = campaign_identity.SecretsCampaignIdentity()
    issued = gateway.issue(port.IssueCampaignIdentityRequest())
    assert len(issued.campaign_id) == 16
    assert all(ch in "0123456789abcdef" for ch in issued.campaign_id)


def test_each_issue_returns_a_different_identity() -> None:
    gateway = campaign_identity.SecretsCampaignIdentity()
    first = gateway.issue(port.IssueCampaignIdentityRequest())
    second = gateway.issue(port.IssueCampaignIdentityRequest())
    assert first.campaign_id != second.campaign_id
