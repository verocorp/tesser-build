from __future__ import annotations

import tesser.app as ts

import app.app as app
import app.repository as repository


class AppLoader(ts.Loader):

    def __init__(self, config_repository: repository.ConfigRepository) -> None:
        self._config_repository = config_repository

    def load(self) -> app.TessercheckApp:
        return app.TessercheckApp(self._config_repository.get())


@ts.load
def load() -> app.TessercheckApp:
    return AppLoader(repository.EnvConfigRepository()).load()
