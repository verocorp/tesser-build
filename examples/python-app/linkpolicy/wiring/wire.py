from __future__ import annotations

import tesser.context as ts

from errors import invalid
from lifecycle import Closeable
from linkpolicy.adapters.gateways.repo_memory import InMemoryVerdictRepository
from linkpolicy.application.service import LinkPolicyService, VerdictRepository
from linkpolicy.client.client import Client
from linkpolicy.wiring.config import Config


@ts.function
def repo_for(cfg: Config) -> tuple[VerdictRepository, Closeable]:
    if cfg.storage == "memory":
        repo = InMemoryVerdictRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "linkpolicy storage coordinate is required")
    raise invalid("unknown_backend", f"linkpolicy storage {cfg.storage!r} not supported")


@ts.function
def build(cfg: Config) -> tuple[Client, Closeable]:
    repo, closeable = repo_for(cfg)
    return LinkPolicyService(repo), closeable
