from __future__ import annotations

import tesser.app as ts

import bootstrap.app as app
import bootstrap.repository as repository


class AppLoader(ts.Loader):

    def __init__(self, configs: repository.ConfigRepository) -> None:
        self._configs = configs

    def load(self) -> app.App:
        return app.App(self._configs.get())


@ts.load
def load() -> app.App:
    return AppLoader(repository.EnvConfigRepository()).load()
