from __future__ import annotations

import tesser.component as ts

import tessercheck.adapters.repositories as repositories
import tessercheck.application as application
import tessercheck.client as client
import tessercheck.component.config as config


class Tessercheck(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self.client: client.Client = application.TessercheckService(
            repositories.FilesystemSourceReader(),
            repositories.FilesystemRulebookSources(),
        )

    def close(self) -> None:
        return None
