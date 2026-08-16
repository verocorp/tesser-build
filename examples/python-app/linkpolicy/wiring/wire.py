from __future__ import annotations

import tesser.context as ts

from tesser.errors import invalid
import linkpolicy.adapters.gateways.repo_memory as repo_memory
import linkpolicy.application.service as service
import linkpolicy.client.client as client
import linkpolicy.wiring.config as config


class LinkPolicy(ts.Wiring):

    def __init__(self, cfg: config.Config) -> None:
        self._repo = self._repo_for(cfg)
        self.client: client.Client = service.LinkPolicyService(self._repo)

    def _repo_for(self, cfg: config.Config) -> repo_memory.InMemoryVerdictRepository:
        if cfg.storage == "memory":
            return repo_memory.InMemoryVerdictRepository()
        if not cfg.storage:
            raise invalid("missing_coordinate", "linkpolicy storage coordinate is required")
        raise invalid("unknown_backend", f"linkpolicy storage {cfg.storage!r} not supported")

    def close(self) -> None:
        self._repo.close()
