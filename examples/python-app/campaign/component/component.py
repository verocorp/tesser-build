from __future__ import annotations

import tesser.component as ts

import campaign.adapters.gateways.campaign_identity as campaign_identity
import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.application.ports.target_policy as target_policy
import campaign.application.service as service
import campaign.client.client as client
import campaign.component.config as config
from tesser.errors import invalid


class Campaign(ts.Component):

    def __init__(self, cfg: config.Config, policy: target_policy.TargetPolicy) -> None:
        self._repo = self._repo_for(cfg)
        self._identity_gateway = campaign_identity.SecretsCampaignIdentity()
        self.client: client.Client = service.CampaignService(
            self._repo, policy, self._identity_gateway
        )

    def _repo_for(self, cfg: config.Config) -> repo_memory.InMemoryCampaignRepository:
        if cfg.storage == "memory":
            return repo_memory.InMemoryCampaignRepository()
        if not cfg.storage:
            raise invalid("missing_coordinate", "campaign storage coordinate is required")
        raise invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")

    def close(self) -> None:
        self._repo.close()
