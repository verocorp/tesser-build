from __future__ import annotations

import tesser.context as ts

from errors import invalid
from lifecycle import Closeable
import linkpolicy.adapters.gateways.repo_memory as repo_memory
import linkpolicy.application.service as service
import linkpolicy.client.client as client
import linkpolicy.wiring.config as config


@ts.function
def repo_for(cfg: config.Config) -> tuple[service.VerdictRepository, Closeable]:
    if cfg.storage == "memory":
        repo = repo_memory.InMemoryVerdictRepository()
        return repo, repo
    if not cfg.storage:
        raise invalid("missing_coordinate", "linkpolicy storage coordinate is required")
    raise invalid("unknown_backend", f"linkpolicy storage {cfg.storage!r} not supported")


@ts.function
def build(cfg: config.Config) -> tuple[client.Client, Closeable]:
    repo, closeable = repo_for(cfg)
    return service.LinkPolicyService(repo), closeable
