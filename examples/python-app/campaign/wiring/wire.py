from __future__ import annotations

import tesser.context as ts

import campaign.adapters.gateways.repo_memory as repo_memory
import campaign.application.service as service
import campaign.client.client as client
import campaign.wiring.config as config
from errors import invalid
from lifecycle import Closeable


@ts.function
def repo_for(cfg: config.Config) -> tuple[service.CampaignRepository, Closeable]:
    if cfg.storage == "memory":
        repo = repo_memory.InMemoryCampaignRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "campaign storage coordinate is required")
    raise invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")


@ts.function
def build(cfg: config.Config, policy: service.TargetPolicy) -> tuple[client.Client, Closeable]:
    repo, closeable = repo_for(cfg)
    return service.CampaignService(repo, policy), closeable
