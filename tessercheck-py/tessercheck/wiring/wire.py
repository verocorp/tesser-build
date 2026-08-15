from __future__ import annotations

import tesser.context as ts

import tessercheck.adapters.repositories as repositories
import tessercheck.application.service as service
import tessercheck.client.client as client
import tessercheck.wiring.config as config
from tesser.lifecycle import Closeable


class NoResources(ts.Wiring):

    def close(self) -> None:
        return None


@ts.function
def build(cfg: config.Config) -> tuple[client.Client, Closeable]:
    return service.TessercheckService(repositories.FilesystemSourceReader()), NoResources()
