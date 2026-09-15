from __future__ import annotations

import tesser.component as ts

import trees.adapters.repositories as repositories
import trees.application as application
import trees.client as client


class Spec(ts.Spec):

    def __init__(self, templates_root: str) -> None:
        self.templates_root = templates_root


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.templates_root = spec.templates_root


class Trees(ts.Component):

    def __init__(self, config: Config) -> None:
        self.client: client.TreesClient = application.TreeService(
            repositories.FilesystemGenerationReader(config.templates_root),
            repositories.FilesystemTreeWriter(),
        )

    def close(self) -> None:
        return None
