from __future__ import annotations

import tesser.component as ts

import specification.adapters.repositories as repositories
import specification.application as application
import specification.client as client
import tesser.errors as errors


class Spec(ts.Spec):

    def __init__(self, storage: str) -> None:
        self.storage = storage


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.storage = spec.storage


class Specification(ts.Component):

    def __init__(self, config: Config) -> None:
        if config.storage != "memory":
            raise errors.invalid("unknown_backend", f"specification storage {config.storage!r} not supported")
        self._specifications = repositories.MemorySpecificationRepository()
        self.client: client.SpecificationClient = application.SpecificationService(self._specifications)

    def close(self) -> None:
        self._specifications.close()
