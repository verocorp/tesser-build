from __future__ import annotations

import tesser.app as ts

import app.app as app
import app.config_repository as config_repository


class AppLoader(ts.Loader):

    def __init__(self, configs: config_repository.ConfigRepository) -> None:
        self._configs = configs

    def load(self) -> app.App:
        return app.App(self._configs.get())


@ts.load
def load() -> app.App:
    return AppLoader(config_repository.EnvConfigRepository()).load()
