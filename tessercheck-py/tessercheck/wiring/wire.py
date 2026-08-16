from __future__ import annotations

import tesser.component as ts

import tessercheck.adapters.repositories.rulebook_sources as rulebook_repository
import tessercheck.adapters.repositories.source_reader as source_repository
import tessercheck.application.service as service
import tessercheck.client.client as client
import tessercheck.wiring.config as config


class Tessercheck(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self.client: client.Client = service.TessercheckService(
            source_repository.FilesystemSourceReader(),
            rulebook_repository.FilesystemRulebookSources(),
        )

    def close(self) -> None:
        return None
