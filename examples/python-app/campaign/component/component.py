from __future__ import annotations

import tesser.component as ts

import campaign.adapters.gateways as gateways
import campaign.adapters.repositories as repositories
import campaign.application as application
import campaign.application.ports as ports
import campaign.client as client
import tesser.errors as errors


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage


class Campaign(ts.Component):

    def __init__(self, config: Config, target_policy: ports.TargetPolicy) -> None:
        if not config.storage:
            raise errors.invalid("missing_coordinate", "campaign storage coordinate is required")
        if config.storage != "memory":
            raise errors.invalid(
                "unknown_backend", f"campaign storage {config.storage!r} not supported"
            )
        self._repo = repositories.InMemoryCampaignRepository()
        self._identity_gateway = gateways.SecretsCampaignIdentity()
        self.client: client.CampaignClient = application.CampaignService(
            self._repo, target_policy, self._identity_gateway, self._repo
        )

    def close(self) -> None:
        self._repo.close()
