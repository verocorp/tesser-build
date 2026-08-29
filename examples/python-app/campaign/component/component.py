from __future__ import annotations

import tesser.component as ts

import campaign.adapters.gateways.campaign_identity as campaign_identity
import campaign.adapters.repositories.repo_memory as repo_memory
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.client.client as client
import campaign.component.config as config
import tesser.errors as errors


class Campaign(ts.Component):

    def __init__(self, cfg: config.Config, policy: target_policy.TargetPolicy) -> None:
        if not cfg.storage:
            raise errors.invalid("missing_coordinate", "campaign storage coordinate is required")
        if cfg.storage != "memory":
            raise errors.invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")
        self._repo = repo_memory.InMemoryCampaignRepository()
        self._identity_gateway = campaign_identity.SecretsCampaignIdentity()
        self.client: client.Client = service.CampaignService(
            self._repo, policy, self._identity_gateway, self._repo
        )

    def close(self) -> None:
        self._repo.close()
