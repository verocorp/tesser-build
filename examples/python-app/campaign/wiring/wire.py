from __future__ import annotations

import tesser.context as ts

from campaign.adapters.gateways.repo_memory import InMemoryCampaignRepository
from campaign.application.service import CampaignRepository, CampaignService, TargetPolicy
from campaign.client.client import Client
from campaign.wiring.config import Config
from errors import invalid
from lifecycle import Closeable


@ts.function
def repo_for(cfg: Config) -> tuple[CampaignRepository, Closeable]:
    if cfg.storage == "memory":
        repo = InMemoryCampaignRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "campaign storage coordinate is required")
    raise invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")


@ts.function
def build(cfg: Config, policy: TargetPolicy) -> tuple[Client, Closeable]:
    repo, closeable = repo_for(cfg)
    return CampaignService(repo, policy), closeable
