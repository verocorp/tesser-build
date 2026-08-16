from __future__ import annotations

import os

import tesser.context as ts

import bootstrap.app as app
import bootstrap.repository as repository


class AppLoader:  # tessercheck:ignore TB051

    def __init__(self, configs: repository.ConfigRepository) -> None:
        self._configs = configs

    def load(self) -> app.App:
        return app.App(self._configs.get())


@ts.function
def load_app() -> app.App:
    return AppLoader(repository.EnvConfigRepository(os.environ)).load()
