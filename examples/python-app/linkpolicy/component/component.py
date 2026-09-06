from __future__ import annotations

import tesser.component as ts

import linkpolicy.adapters.repositories as repositories
import linkpolicy.application as application
import linkpolicy.client as client
import tesser.errors as errors


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage


class LinkPolicy(ts.Component):

    def __init__(self, config: Config) -> None:
        if not config.storage:
            raise errors.invalid("missing_coordinate", "linkpolicy storage coordinate is required")
        if config.storage != "memory":
            raise errors.invalid(
                "unknown_backend", f"linkpolicy storage {config.storage!r} not supported"
            )
        self._repo = repositories.InMemoryVerdictRepository()
        self.client: client.LinkPolicyClient = application.LinkPolicyService(self._repo)

    def close(self) -> None:
        self._repo.close()
