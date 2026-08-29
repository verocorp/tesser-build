from __future__ import annotations

import tesser.component as ts

import tesser.errors as errors
import linkpolicy.adapters.repositories.repo_memory as repo_memory
import linkpolicy.application.service as service
import linkpolicy.client.client as client
import linkpolicy.component.config as config


class LinkPolicy(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        if not cfg.storage:
            raise errors.invalid("missing_coordinate", "linkpolicy storage coordinate is required")
        if cfg.storage != "memory":
            raise errors.invalid("unknown_backend", f"linkpolicy storage {cfg.storage!r} not supported")
        self._repo = repo_memory.InMemoryVerdictRepository()
        self.client: client.Client = service.LinkPolicyService(self._repo)

    def close(self) -> None:
        self._repo.close()
