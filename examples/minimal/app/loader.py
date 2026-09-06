from __future__ import annotations

import tesser.app as ts

import app.app as app
import app.config_repository as config_repository


class AppLoader(ts.Loader):

    def __init__(self, app_config_repository: config_repository.AppConfigRepository) -> None:
        self._app_config_repository = app_config_repository

    def load(self) -> app.MinimalApp:
        return app.MinimalApp(self._app_config_repository.get())


@ts.load
def load() -> app.MinimalApp:
    return AppLoader(config_repository.EnvConfigRepository()).load()
