from __future__ import annotations

from campaign.adapters.gateways.repo_memory import InMemoryLinkRepository
from campaign.application.service import CampaignService, LinkRepository
from campaign.client import Client, TargetChecker
from campaign.wiring.config import Config
from errors import invalid
from lifecycle import Closeable


def repo_for(cfg: Config) -> tuple[LinkRepository, Closeable]:
    if cfg.storage == "memory":
        repo = InMemoryLinkRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "campaign storage coordinate is required")
    raise invalid("unknown_backend", f"campaign storage {cfg.storage!r} not supported")


def build(cfg: Config, checker: TargetChecker) -> tuple[Client, Closeable]:
    repo, closeable = repo_for(cfg)
    return CampaignService(repo, checker), closeable
