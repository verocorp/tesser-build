from __future__ import annotations

import tesser.app as ts

import repo.wiring.wire as repo_wire

import bootstrap.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        self.repo = repo_wire.Repo(cfg.repo)

    def close(self) -> None:
        self.repo.close()
