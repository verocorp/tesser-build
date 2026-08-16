from __future__ import annotations

import tesser.app as ts

import repo.wiring.config as repo_config


class Spec(ts.Spec):

    def __init__(self, repo: repo_config.Config) -> None:
        self.repo = repo


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.repo = spec.repo
