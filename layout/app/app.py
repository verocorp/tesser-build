from __future__ import annotations

import tesser.app as ts

import repo.component.component as repo_component

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        self.repo = repo_component.Repo(cfg.repo)

    def close(self) -> None:
        self.repo.close()
