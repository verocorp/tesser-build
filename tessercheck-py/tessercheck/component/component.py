from __future__ import annotations

import tesser.component as ts

import tessercheck.adapters.repositories as repositories
import tessercheck.application as application
import tessercheck.client as client


class Spec(ts.Spec):

    def __init__(self) -> None:
        return None


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        return None


class Tessercheck(ts.Component):

    def __init__(self, config: Config) -> None:
        self.client: client.TessercheckClient = application.TessercheckService(
            repositories.FilesystemSourceReader(),
            repositories.FilesystemSourceWriter(),
            repositories.FilesystemRulebookSources(),
        )

    def close(self) -> None:
        return None
